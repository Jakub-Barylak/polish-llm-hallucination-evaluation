from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from . import VerificationError
from .api import (
    AnnotationValidationError,
    RateLimitCoordinator,
    batch_endpoint,
    build_batch_request,
    build_request_data,
    request_annotation,
    response_text,
    web_search_audit,
)
from .common import load_repo_env, read_jsonl, sha256_bytes, utc_timestamp
from .data import (
    annotation_input,
    answer_key,
    item_sha256,
    load_answers,
    load_questions,
    render_prompt,
    selected_answers,
)
from .storage import (
    annotator_config,
    append_jsonl,
    completed_annotations,
    configs_compatible,
    export_annotations,
    read_archive,
    write_bytes_atomic,
    write_json_atomic,
    write_jsonl_atomic,
)
from .schema import json_default, parse_annotation


RESEARCH_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = RESEARCH_DIR.parent


def _load_run(args: argparse.Namespace) -> tuple[
    bytes, dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    # Odcisk protokołu i treść requestu nie mogą zależeć od ustawienia
    # core.autocrlf ani systemu operacyjnego, na którym przygotowano batch.
    prompt_bytes = (
        args.prompt.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    )
    _, questions_by_id = load_questions(args.questions)
    answers = load_answers(args.answers, questions_by_id)
    config = annotator_config(
        args.experiment, args.prompt, prompt_bytes, args.model, RESEARCH_DIR
    )
    return prompt_bytes, questions_by_id, answers, config


def annotate(args: argparse.Namespace) -> int:
    prompt_bytes, questions_by_id, answers, config = _load_run(args)
    prompt = prompt_bytes.decode("utf-8")
    completed = completed_annotations(read_archive(args.archive), config)
    selected = selected_answers(answers, args.ids, args.models, args.limit)

    pending: list[tuple[dict[str, Any], dict[str, Any], str, str]] = []
    for answer in selected:
        model_id, question_id = answer_key(answer)
        question = questions_by_id[question_id]
        fingerprint = item_sha256(question, answer, args.experiment)
        if not args.force and (model_id, question_id, fingerprint) in completed:
            continue
        rendered = render_prompt(
            prompt, annotation_input(question, answer, args.experiment)
        )
        pending.append((answer, question, fingerprint, rendered))

    print(f"Wybrano {len(selected)} odpowiedzi; do adnotacji: {len(pending)}.")
    if not pending:
        export_annotations(
            questions_by_id=questions_by_id,
            answers=answers,
            archive_path=args.archive,
            output_path=args.output,
            config=config,
            experiment=args.experiment,
        )
        return 0

    load_repo_env(REPO_DIR / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise VerificationError(
            f"Brak OPENAI_API_KEY w środowisku lub pliku {REPO_DIR / '.env'}"
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise VerificationError(
            "Brak pakietu openai. Uruchom skrypt przez uv z katalogu research."
        ) from exc

    client = OpenAI(max_retries=0)
    rate_limit = RateLimitCoordinator()
    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures: dict[
            Future[tuple[dict[str, Any], dict[str, Any]]],
            tuple[dict[str, Any], dict[str, Any], str],
        ] = {}
        for answer, question, fingerprint, rendered in pending:
            model_id, question_id = answer_key(answer)
            future = executor.submit(
                request_annotation,
                client,
                args.experiment,
                args.model,
                rendered,
                question.get("source_url") if args.experiment.web_search else None,
                model_id,
                question_id,
                args.max_retries,
                rate_limit,
            )
            futures[future] = (answer, question, fingerprint)

        for position, future in enumerate(as_completed(futures), start=1):
            answer, question, fingerprint = futures[future]
            model_id, question_id = answer_key(answer)
            base_event = {
                "timestamp": utc_timestamp(),
                "question_id": question_id,
                "model_id": model_id,
                "item_sha256": fingerprint,
                "config": config,
            }
            try:
                annotation, api_data = future.result()
                valid_source = (
                    not args.experiment.web_search
                    or (
                        api_data["web_search_audit"]["calls"] > 0
                        and (
                            not args.experiment.require_exact_source
                            or api_data["web_search_audit"][
                                "expected_source_consulted"
                            ]
                        )
                    )
                )
                event = {
                    **base_event,
                    "status": "ok" if valid_source else "invalid_source",
                    **api_data,
                    "annotation": annotation,
                }
                append_jsonl(args.archive, event)
                if valid_source:
                    print(
                        f"[{position}/{len(pending)}] OK {model_id} / "
                        f"{question_id}: {annotation['label']}"
                    )
                else:
                    errors += 1
                    print(
                        f"[{position}/{len(pending)}] NIEWAŻNE ŹRÓDŁO "
                        f"{model_id} / {question_id}: wskazany URL nie wystąpił "
                        "w źródłach web search",
                        file=sys.stderr,
                    )
            except AnnotationValidationError as exc:
                errors += 1
                append_jsonl(
                    args.archive,
                    {
                        **base_event,
                        "status": "invalid_annotation",
                        **exc.api_data,
                        "error": repr(exc),
                    },
                )
                print(
                    f"[{position}/{len(pending)}] NIEWAŻNA ADNOTACJA "
                    f"{model_id} / {question_id}: {exc}",
                    file=sys.stderr,
                )
            except Exception as exc:
                errors += 1
                append_jsonl(
                    args.archive,
                    {**base_event, "status": "error", "error": repr(exc)},
                )
                print(
                    f"[{position}/{len(pending)}] BŁĄD {model_id} / "
                    f"{question_id}: {exc}",
                    file=sys.stderr,
                )

    export_annotations(
        questions_by_id=questions_by_id,
        answers=answers,
        archive_path=args.archive,
        output_path=args.output,
        config=config,
        experiment=args.experiment,
    )
    return 1 if errors else 0


def _batch_custom_id(question_id: str, fingerprint: str) -> str:
    safe_question_id = "".join(
        character if character.isascii() and character.isalnum() else "-"
        for character in question_id
    ).strip("-")
    safe_question_id = safe_question_id[:24] or "question"
    return f"{safe_question_id}-{fingerprint[:32]}"


def prepare_batch(args: argparse.Namespace) -> int:
    """Zapisuje oczekujące adnotacje jako wejściowy JSONL Batch API."""
    prompt_bytes, questions_by_id, answers, config = _load_run(args)
    prompt = prompt_bytes.decode("utf-8")
    completed = completed_annotations(read_archive(args.archive), config)
    selected = selected_answers(answers, args.ids, args.models, args.limit)

    requests: list[dict[str, Any]] = []
    custom_ids: set[str] = set()
    skipped = 0
    for answer in selected:
        model_id, question_id = answer_key(answer)
        question = questions_by_id[question_id]
        fingerprint = item_sha256(question, answer, args.experiment)
        if not args.force and (model_id, question_id, fingerprint) in completed:
            skipped += 1
            continue
        rendered = render_prompt(
            prompt, annotation_input(question, answer, args.experiment)
        )
        custom_id = _batch_custom_id(question_id, fingerprint)
        if custom_id in custom_ids:
            raise VerificationError(f"Powtórzony batch custom_id: {custom_id}")
        custom_ids.add(custom_id)
        requests.append(
            build_batch_request(
                custom_id=custom_id,
                experiment=args.experiment,
                model=args.model,
                rendered_prompt=rendered,
                source_url=(
                    question.get("source_url")
                    if args.experiment.web_search
                    else None
                ),
            )
        )

    write_jsonl_atomic(args.batch_input, requests)
    print(
        f"Wybrano {len(selected)} odpowiedzi; pominięto ukończone: {skipped}; "
        f"zapisano do batcha: {len(requests)}."
    )
    print(f"Plik Batch API: {args.batch_input}")
    if not requests:
        print("Brak oczekujących żądań; zapisany plik jest pusty.")
    return 0


def _json_value(value: Any) -> dict[str, Any]:
    serialized = json.loads(json.dumps(value, default=json_default, ensure_ascii=False))
    if not isinstance(serialized, dict):
        raise VerificationError("OpenAI API zwróciło niepoprawny obiekt")
    return serialized


def _openai_client() -> Any:
    load_repo_env(REPO_DIR / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise VerificationError(
            f"Brak OPENAI_API_KEY w środowisku lub pliku {REPO_DIR / '.env'}"
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise VerificationError(
            "Brak pakietu openai. Uruchom skrypt przez uv z katalogu research."
        ) from exc
    return OpenAI()


def _read_batch_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VerificationError(
            f"Nie znaleziono stanu batcha: {path}. Najpierw uruchom submit-batch."
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Niepoprawny JSON stanu batcha {path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"Stan batcha {path} nie jest obiektem JSON")
    return value


def _state_batch_id(state: dict[str, Any]) -> str | None:
    batch = state.get("batch")
    batch_id = batch.get("id") if isinstance(batch, dict) else None
    return batch_id if isinstance(batch_id, str) and batch_id else None


def _validated_batch_input(args: argparse.Namespace) -> tuple[bytes, int]:
    rows = read_jsonl(args.batch_input, "pliku wejściowego Batch API")
    if not rows:
        raise VerificationError("Plik wejściowy Batch API jest pusty")
    expected_endpoint = batch_endpoint(args.experiment)
    endpoints = {row.get("url") for row in rows}
    if endpoints != {expected_endpoint}:
        raise VerificationError(
            f"Plik batcha musi zawierać wyłącznie endpoint {expected_endpoint}"
        )
    models = {
        body.get("model")
        for row in rows
        for body in [row.get("body")]
        if isinstance(body, dict)
    }
    if models != {args.model}:
        raise VerificationError(
            f"Plik batcha musi zawierać wyłącznie model {args.model}"
        )
    custom_ids = [row.get("custom_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in custom_ids):
        raise VerificationError("Każde żądanie batcha musi mieć custom_id")
    if len(custom_ids) != len(set(custom_ids)):
        raise VerificationError("Plik wejściowy zawiera powtórzone custom_id")
    return args.batch_input.read_bytes(), len(rows)


def submit_batch(args: argparse.Namespace) -> int:
    """Przesyła wejściowy JSONL i uruchamia zadanie Batch API."""
    input_bytes, request_count = _validated_batch_input(args)
    _, _, _, config = _load_run(args)
    if args.batch_state.exists() and not args.resubmit:
        state = _read_batch_state(args.batch_state)
        existing_id = _state_batch_id(state)
        if existing_id is not None:
            raise VerificationError(
                f"Stan zawiera już batch {existing_id}. Użyj batch-status albo "
                "jawnie --resubmit, aby utworzyć kolejne płatne zadanie."
            )

    client = _openai_client()
    with args.batch_input.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="batch")
    uploaded_data = _json_value(uploaded)
    input_file_id = uploaded_data.get("id")
    if not isinstance(input_file_id, str) or not input_file_id:
        raise VerificationError("Files API nie zwróciło input_file_id")

    state: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": args.experiment.experiment_id,
        "batch_input_sha256": sha256_bytes(input_bytes),
        "request_count": request_count,
        "config": config,
        "input_file": uploaded_data,
        "batch": None,
    }
    # Zachowaj ID uploadu nawet wtedy, gdy samo utworzenie batcha się nie uda.
    write_json_atomic(args.batch_state, state)
    batch = client.batches.create(
        input_file_id=input_file_id,
        endpoint=batch_endpoint(args.experiment),
        completion_window="24h",
        metadata={"experiment_id": args.experiment.experiment_id},
    )
    batch_data = _json_value(batch)
    state["batch"] = batch_data
    write_json_atomic(args.batch_state, state)
    print(f"Utworzono batch: {batch_data.get('id')}")
    print(f"Status: {batch_data.get('status')}")
    print(f"Stan zapisano w: {args.batch_state}")
    return 0


def _retrieve_batch(args: argparse.Namespace, client: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _read_batch_state(args.batch_state)
    batch_id = args.batch_id or _state_batch_id(state)
    if batch_id is None:
        raise VerificationError("Stan nie zawiera batch_id")
    batch_data = _json_value(client.batches.retrieve(batch_id))
    state["batch"] = batch_data
    write_json_atomic(args.batch_state, state)
    return state, batch_data


def _request_counts_text(batch: dict[str, Any]) -> str:
    counts = batch.get("request_counts")
    if not isinstance(counts, dict):
        return ""
    return (
        f"; żądania: {counts.get('completed', 0)}/{counts.get('total', 0)} "
        f"ukończonych, {counts.get('failed', 0)} nieudanych"
    )


def batch_status(args: argparse.Namespace) -> int:
    """Odświeża i zapisuje status zadania Batch API."""
    _, batch = _retrieve_batch(args, _openai_client())
    print(
        f"Batch {batch.get('id')}: {batch.get('status')}"
        f"{_request_counts_text(batch)}"
    )
    if batch.get("output_file_id"):
        print(f"output_file_id: {batch['output_file_id']}")
    if batch.get("error_file_id"):
        print(f"error_file_id: {batch['error_file_id']}")
    return 0


def _file_content_bytes(client: Any, file_id: str) -> bytes:
    response = client.files.content(file_id)
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content
    text = getattr(response, "text", None)
    if callable(text):
        text = text()
    if isinstance(text, str):
        return text.encode("utf-8")
    read = getattr(response, "read", None)
    if callable(read):
        content = read()
        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode("utf-8")
    raise VerificationError(f"Nie można odczytać zawartości pliku {file_id}")


def _batch_identity_map(
    args: argparse.Namespace,
    questions_by_id: dict[str, dict[str, Any]],
    answers: list[dict[str, Any]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any], str]]:
    identities: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {}
    for answer in answers:
        _, question_id = answer_key(answer)
        question = questions_by_id[question_id]
        fingerprint = item_sha256(question, answer, args.experiment)
        custom_id = _batch_custom_id(question_id, fingerprint)
        if custom_id in identities:
            raise VerificationError(f"Powtórzony batch custom_id: {custom_id}")
        identities[custom_id] = (answer, question, fingerprint)
    return identities


def _import_batch_results(
    args: argparse.Namespace,
    state: dict[str, Any],
    batch: dict[str, Any],
    result_rows: list[dict[str, Any]],
) -> tuple[int, int]:
    _, questions_by_id, answers, current_config = _load_run(args)
    stored_config = state.get("config")
    if not configs_compatible(stored_config, current_config):
        raise VerificationError(
            "Konfiguracja lub prompt zmieniły się od wysłania batcha; "
            "wyniki nie zostały zaimportowane."
        )
    expected_sha = state.get("batch_input_sha256")
    actual_sha = sha256_bytes(args.batch_input.read_bytes())
    if expected_sha != actual_sha:
        raise VerificationError(
            "Plik batch_input.jsonl zmienił się od wysłania batcha"
        )

    input_rows = read_jsonl(args.batch_input, "pliku wejściowego Batch API")
    inputs = {row.get("custom_id"): row for row in input_rows}
    identities = _batch_identity_map(args, questions_by_id, answers)
    for row in result_rows:
        custom_id = row.get("custom_id")
        if custom_id not in inputs or custom_id not in identities:
            raise VerificationError(
                f"Wynik batcha ma nieznany custom_id: {custom_id!r}"
            )

    batch_id = batch.get("id")
    archive = read_archive(args.archive)
    imported_keys = {
        (details.get("batch_id"), details.get("custom_id"))
        for event in archive
        for details in [event.get("batch")]
        if isinstance(details, dict)
    }
    imported = 0
    failures = 0
    for row in result_rows:
        custom_id = row["custom_id"]
        if (batch_id, custom_id) in imported_keys:
            continue
        answer, question, fingerprint = identities[custom_id]
        model_id, question_id = answer_key(answer)
        response_wrapper = row.get("response")
        status_code = (
            response_wrapper.get("status_code")
            if isinstance(response_wrapper, dict)
            else None
        )
        raw_response = (
            response_wrapper.get("body")
            if isinstance(response_wrapper, dict)
            else None
        )
        batch_details = {
            "batch_id": batch_id,
            "custom_id": custom_id,
            "request_id": row.get("id"),
        }
        base_event = {
            "timestamp": utc_timestamp(),
            "question_id": question_id,
            "model_id": model_id,
            "item_sha256": fingerprint,
            "config": current_config,
            "batch": batch_details,
            "request": inputs[custom_id].get("body"),
        }
        if status_code != 200 or not isinstance(raw_response, dict):
            failures += 1
            append_jsonl(
                args.archive,
                {
                    **base_event,
                    "status": "batch_error",
                    "response": raw_response,
                    "error": row.get("error") or response_wrapper,
                },
            )
            imported += 1
            continue

        api_data: dict[str, Any] = {"response": raw_response}
        if args.experiment.web_search:
            source_url = question.get("source_url")
            if not isinstance(source_url, str) or not source_url:
                raise VerificationError("Brak source_url w audycie web search")
            api_data["web_search_audit"] = web_search_audit(
                raw_response, source_url
            )
        try:
            content = response_text(raw_response, args.experiment.api_endpoint)
            if not content:
                raise VerificationError(
                    "Odpowiedź Batch API nie zawiera treści annotatora"
                )
            annotation = parse_annotation(content)
            audit = api_data.get("web_search_audit")
            valid_source = (
                not args.experiment.web_search
                or (
                    isinstance(audit, dict)
                    and audit.get("calls", 0) > 0
                    and (
                        not args.experiment.require_exact_source
                        or audit.get("expected_source_consulted") is True
                    )
                )
            )
            status = "ok" if valid_source else "invalid_source"
            if not valid_source:
                failures += 1
            event = {
                **base_event,
                "status": status,
                **api_data,
                "annotation": annotation,
            }
        except VerificationError as exc:
            failures += 1
            event = {
                **base_event,
                "status": "invalid_annotation",
                **api_data,
                "error": str(exc),
            }
        append_jsonl(args.archive, event)
        imported += 1

    export_annotations(
        questions_by_id=questions_by_id,
        answers=answers,
        archive_path=args.archive,
        output_path=args.output,
        config=current_config,
        experiment=args.experiment,
    )
    return imported, failures


def collect_batch(args: argparse.Namespace) -> int:
    """Pobiera pliki zakończonego batcha i importuje wyniki do archiwum."""
    client = _openai_client()
    state, batch = _retrieve_batch(args, client)
    status = batch.get("status")
    if status not in {"completed", "failed", "expired", "cancelled"}:
        raise VerificationError(
            f"Batch ma status {status!r}; wyniki nie są jeszcze gotowe"
        )

    result_rows: list[dict[str, Any]] = []
    output_file_id = batch.get("output_file_id")
    if isinstance(output_file_id, str) and output_file_id:
        output_data = _file_content_bytes(client, output_file_id)
        write_bytes_atomic(args.batch_output, output_data)
        result_rows.extend(read_jsonl(args.batch_output, "wyników Batch API"))
        print(f"Pobrano wyniki: {args.batch_output}")
    error_file_id = batch.get("error_file_id")
    if isinstance(error_file_id, str) and error_file_id:
        error_data = _file_content_bytes(client, error_file_id)
        write_bytes_atomic(args.batch_errors, error_data)
        result_rows.extend(read_jsonl(args.batch_errors, "błędów Batch API"))
        print(f"Pobrano błędy: {args.batch_errors}")
    if not result_rows:
        raise VerificationError("Batch nie udostępnił żadnych wyników ani błędów")

    imported, failures = _import_batch_results(args, state, batch, result_rows)
    print(
        f"Zaimportowano nowych rekordów: {imported}; "
        f"nieudane lub nieważne: {failures}."
    )
    return 1 if failures else 0


def export_command(args: argparse.Namespace) -> int:
    _, questions_by_id, answers, config = _load_run(args)
    export_annotations(
        questions_by_id=questions_by_id,
        answers=answers,
        archive_path=args.archive,
        output_path=args.output,
        config=config,
        experiment=args.experiment,
    )
    return 0


def preview(args: argparse.Namespace) -> int:
    prompt = args.prompt.read_text(encoding="utf-8")
    _, questions_by_id = load_questions(args.questions)
    answers = load_answers(args.answers, questions_by_id)
    selected = selected_answers(answers, args.ids, args.models, limit=1)
    if not selected:
        raise VerificationError("Brak odpowiedzi spełniającej podane filtry")
    answer = selected[0]
    question = questions_by_id[answer_key(answer)[1]]
    rendered = render_prompt(
        prompt, annotation_input(question, answer, args.experiment)
    )
    request = build_request_data(
        experiment=args.experiment,
        model=args.model,
        rendered_prompt=rendered,
        source_url=(
            question.get("source_url") if args.experiment.web_search else None
        ),
    )
    print(json.dumps(request, ensure_ascii=False, indent=2))
    return 0


def stats(args: argparse.Namespace) -> int:
    output = read_jsonl(args.output, "pliku etykiet") if args.output.exists() else []
    archive = read_archive(args.archive)
    source_audits = [
        row["web_search_audit"]
        for row in output
        if isinstance(row.get("web_search_audit"), dict)
    ]
    result = {
        "experiment_id": args.experiment.experiment_id,
        "exported_annotations": len(output),
        "labels": dict(Counter(row.get("label", "unknown") for row in output)),
        "models": dict(Counter(row.get("model_id", "unknown") for row in output)),
        "categories": dict(
            Counter(row.get("category", "unknown") for row in output)
        ),
        "archive_events": len(archive),
        "archive_statuses": dict(
            Counter(event.get("status", "unknown") for event in archive)
        ),
        "expected_source_consulted": dict(
            Counter(
                audit.get("expected_source_consulted", "unknown")
                for audit in source_audits
            )
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
