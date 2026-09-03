from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .common import canonical_json, read_jsonl, sha256_bytes
from .config import Experiment
from .data import annotation_input, answer_key, item_sha256
from .schema import RESPONSE_FORMAT


RUNNER_VERSION = "verify_answers_v3"
WEB_AUDIT_VERSION = "web_search_audit_v3"


def _runner_sha256(research_dir: Path) -> str:
    """Odcisk wejścia CLI i wszystkich modułów wykonawczych."""
    paths = [research_dir / "verify_answers.py"]
    paths.extend(sorted((research_dir / "verification").glob("*.py")))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(research_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def annotator_config(
    experiment: Experiment,
    prompt_path: Path,
    prompt_bytes: bytes,
    model: str,
    research_dir: Path,
) -> dict[str, Any]:
    return {
        "experiment_id": experiment.experiment_id,
        "experiment_config": experiment.config_path.name,
        "experiment_config_sha256": experiment.config_sha256,
        "runner_version": RUNNER_VERSION,
        "runner_sha256": _runner_sha256(research_dir),
        "web_audit_version": WEB_AUDIT_VERSION if experiment.web_search else None,
        "api_endpoint": experiment.api_endpoint,
        "model": model,
        "temperature": (
            experiment.temperature
            if experiment.api_endpoint == "chat_completions"
            else None
        ),
        "reasoning_effort": (
            experiment.reasoning_effort
            if experiment.api_endpoint == "responses"
            else None
        ),
        "max_tokens": experiment.max_output_tokens,
        "input_fields": list(experiment.input_fields),
        "web_search": experiment.web_search,
        "prompt_version": prompt_path.stem,
        "prompt_sha256": sha256_bytes(prompt_bytes),
        "response_schema_sha256": sha256_bytes(canonical_json(RESPONSE_FORMAT)),
    }


def read_archive(path: Path) -> list[dict[str, Any]]:
    return [] if not path.exists() else read_jsonl(path, "archiwum adnotacji")


def completed_annotations(
    archive: list[dict[str, Any]], config: dict[str, Any]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    completed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in archive:
        if (
            event.get("status") != "ok"
            or not configs_compatible(event.get("config"), config)
            or not isinstance(event.get("annotation"), dict)
        ):
            continue
        key = (
            event.get("model_id"),
            event.get("question_id"),
            event.get("item_sha256"),
        )
        if all(isinstance(value, str) and value for value in key):
            completed[key] = event
    return completed


def configs_compatible(stored: Any, current: dict[str, Any]) -> bool:
    """Porównuje protokół, zachowując pełny SHA kodu tylko do audytu.

    Zmiany techniczne są wersjonowane przez runner_version, a zmiany audytu
    źródeł niezależnie przez web_audit_version. Dzięki temu poprawka dotycząca
    wyłącznie web search nie unieważnia adnotacji eksperymentów bez narzędzi.
    """
    if not isinstance(stored, dict):
        return False

    def protocol_config(value: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(value)
        normalized.pop("runner_sha256", None)
        if normalized.get("web_audit_version") is None:
            normalized.pop("web_audit_version", None)
        return normalized

    return protocol_config(stored) == protocol_config(current)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            for record in records:
                handle.write(
                    json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    """Atomowo zapisuje kompletny plik JSONL, także gdy lista jest pusta."""
    _atomic_write_jsonl(path, records)


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Atomowo zapisuje pobraną zawartość pliku Batch API."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    """Atomowo zapisuje pojedynczy obiekt JSON."""
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    write_bytes_atomic(path, data)


def _output_record(
    question: dict[str, Any],
    answer: dict[str, Any],
    event: dict[str, Any],
    experiment: Experiment,
) -> dict[str, Any]:
    annotation = event["annotation"]
    model_id, question_id = answer_key(answer)
    response = event.get("response")
    usage = response.get("usage") if isinstance(response, dict) else None
    annotator = {
        "model": event["config"]["model"],
        "temperature": event["config"]["temperature"],
        "reasoning_effort": event["config"]["reasoning_effort"],
        "input_fields": event["config"]["input_fields"],
        "prompt_version": event["config"]["prompt_version"],
        "prompt_sha256": event["config"]["prompt_sha256"],
        "annotated_at": event["timestamp"],
    }
    if isinstance(usage, dict):
        annotator["usage"] = usage
    record = {
        "experiment_id": experiment.experiment_id,
        "id": question_id,
        "category": question["category"],
        "subcategory": question.get("subcategory", ""),
        "question_pl": question["question_pl"],
        "gold_answer": question["gold_answer"],
        "accepted_answers": question["accepted_answers"],
        "source_url": question.get("source_url", ""),
        "extraction_date": question.get("extraction_date", ""),
        "model_id": model_id,
        "response": answer["response"],
        "annotator_input": annotation_input(question, answer, experiment),
        "label": annotation["label"],
        "confidence": annotation["confidence"],
        "analysis": annotation["analysis"],
        "matched_answer": annotation["matched_answer"],
        "false_claims": annotation["false_claims"],
        "item_sha256": event["item_sha256"],
        "annotator": annotator,
    }
    if experiment.web_search:
        record["web_search_audit"] = event.get("web_search_audit", {})
    return record


def export_annotations(
    *,
    questions_by_id: dict[str, dict[str, Any]],
    answers: list[dict[str, Any]],
    archive_path: Path,
    output_path: Path,
    config: dict[str, Any],
    experiment: Experiment,
) -> int:
    completed = completed_annotations(read_archive(archive_path), config)
    records: list[dict[str, Any]] = []
    for answer in answers:
        model_id, question_id = answer_key(answer)
        question = questions_by_id[question_id]
        fingerprint = item_sha256(question, answer, experiment)
        event = completed.get((model_id, question_id, fingerprint))
        if event is not None:
            records.append(_output_record(question, answer, event, experiment))
    _atomic_write_jsonl(output_path, records)
    print(f"Zapisano {len(records)}/{len(answers)} etykiet do {output_path}.")
    return len(records)
