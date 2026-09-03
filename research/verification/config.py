from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import VerificationError


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    description: str
    input_fields: tuple[str, ...]
    evidence_field: str
    prompt_path: Path
    output_path: Path
    archive_path: Path
    batch_input_path: Path
    batch_output_path: Path
    batch_error_path: Path
    batch_state_path: Path
    api_endpoint: str
    model: str
    temperature: float
    reasoning_effort: str
    max_output_tokens: int
    web_search: bool
    web_search_context_size: str | None
    require_exact_source: bool
    config_path: Path
    config_sha256: str


def _required(
    values: dict[str, Any], key: str, expected_type: type, context: str
) -> Any:
    value = values.get(key)
    if not isinstance(value, expected_type) or isinstance(value, bool):
        raise VerificationError(
            f"{context}: pole {key!r} musi mieć typ {expected_type.__name__}"
        )
    return value


def load_experiments(path: Path) -> dict[str, Experiment]:
    try:
        config_bytes = path.read_bytes()
        data = tomllib.loads(config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise VerificationError(f"Nie można wczytać konfiguracji {path}: {exc}") from exc

    if data.get("config_version") != 1:
        raise VerificationError("Nieobsługiwana config_version eksperymentów")
    defaults = data.get("defaults")
    definitions = data.get("experiments")
    if not isinstance(defaults, dict) or not isinstance(definitions, dict):
        raise VerificationError("Konfiguracja wymaga tabel defaults i experiments")

    default_endpoint = _required(defaults, "api_endpoint", str, "defaults")
    supported_endpoints = {"responses", "chat_completions"}
    if default_endpoint not in supported_endpoints:
        raise VerificationError("Nieobsługiwany domyślny api_endpoint")
    model = _required(defaults, "model", str, "defaults")
    temperature = _required(defaults, "temperature", float, "defaults")
    reasoning_effort = _required(defaults, "reasoning_effort", str, "defaults")
    default_max_output_tokens = _required(
        defaults, "max_output_tokens", int, "defaults"
    )
    if default_max_output_tokens < 1:
        raise VerificationError("max_output_tokens musi być większe od zera")

    experiments: dict[str, Experiment] = {}
    for experiment_id, raw in definitions.items():
        context = f"experiments.{experiment_id}"
        if not isinstance(raw, dict):
            raise VerificationError(f"{context} musi być tabelą TOML")
        fields = raw.get("input_fields")
        allowed_fields = {
            "question_id",
            "category",
            "question",
            "gold_answer",
            "accepted_answers",
            "reference_passage",
            "source_url",
            "model_response",
        }
        if (
            not isinstance(fields, list)
            or any(not isinstance(field, str) for field in fields)
            or len(fields) != len(set(fields))
            or not 5 <= len(fields) <= 7
            or tuple(fields[:3]) != ("question_id", "category", "question")
            or fields[-1] != "model_response"
            or not set(fields).issubset(allowed_fields)
        ):
            raise VerificationError(f"{context}: niepoprawne input_fields")
        evidence_fields = set(fields) & {"reference_passage", "source_url"}
        has_answer_key = {"gold_answer", "accepted_answers"}.issubset(fields)
        if len(evidence_fields) > 1 or (not evidence_fields and not has_answer_key):
            raise VerificationError(
                f"{context}: wymagany jest klucz odpowiedzi, pasaż albo source_url"
            )
        evidence_field = (
            evidence_fields.pop() if evidence_fields else "gold_answer"
        )

        api_endpoint = raw.get("api_endpoint", default_endpoint)
        if api_endpoint not in supported_endpoints:
            raise VerificationError(f"{context}: nieobsługiwany api_endpoint")

        max_output_tokens = raw.get(
            "max_output_tokens", default_max_output_tokens
        )
        if (
            not isinstance(max_output_tokens, int)
            or isinstance(max_output_tokens, bool)
            or max_output_tokens < 1
        ):
            raise VerificationError(
                f"{context}: max_output_tokens musi być dodatnią liczbą całkowitą"
            )

        web_search = raw.get("web_search")
        if not isinstance(web_search, bool):
            raise VerificationError(f"{context}: web_search musi być bool")
        if web_search != (evidence_field == "source_url"):
            raise VerificationError(
                f"{context}: source_url wymaga web_search, a inne źródło go wyklucza"
            )
        if web_search and api_endpoint != "responses":
            raise VerificationError(f"{context}: web_search wymaga Responses API")
        context_size = raw.get("web_search_context_size")
        if web_search and context_size not in {"low", "medium", "high"}:
            raise VerificationError(f"{context}: niepoprawny kontekst web search")
        require_exact_source = raw.get("require_exact_source", False)
        if not isinstance(require_exact_source, bool):
            raise VerificationError(f"{context}: require_exact_source musi być bool")

        # Katalog artefaktów jest ustawieniem operacyjnym przebiegu, a nie
        # częścią protokołu badawczego. Można go zmieniać między
        # powtórzeniami bez unieważniania zgodnych adnotacji.
        protocol_definition = dict(raw)
        protocol_definition.pop("artifacts_dir", None)
        protocol_bytes = json.dumps(
            {
                "config_version": data["config_version"],
                "defaults": defaults,
                "experiment_id": experiment_id,
                "experiment": protocol_definition,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        configured_output = path.parent / _required(raw, "output", str, context)
        configured_archive = path.parent / _required(raw, "archive", str, context)
        artifacts_dir_value = raw.get("artifacts_dir")
        if artifacts_dir_value is not None and not isinstance(
            artifacts_dir_value, str
        ):
            raise VerificationError(f"{context}: artifacts_dir musi być napisem")
        artifacts_dir = (
            path.parent / artifacts_dir_value
            if artifacts_dir_value is not None
            else configured_archive.parent
        )
        output_path = (
            artifacts_dir / configured_output.name
            if artifacts_dir_value is not None
            else configured_output
        )
        archive_path = (
            artifacts_dir / configured_archive.name
            if artifacts_dir_value is not None
            else configured_archive
        )

        experiments[experiment_id] = Experiment(
            experiment_id=experiment_id,
            description=_required(raw, "description", str, context),
            input_fields=tuple(fields),
            evidence_field=evidence_field,
            prompt_path=path.parent / _required(raw, "prompt", str, context),
            output_path=output_path,
            archive_path=archive_path,
            batch_input_path=artifacts_dir / "batch_input.jsonl",
            batch_output_path=artifacts_dir / "batch_output.jsonl",
            batch_error_path=artifacts_dir / "batch_errors.jsonl",
            batch_state_path=artifacts_dir / "batch_state.json",
            api_endpoint=api_endpoint,
            model=model,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            web_search=web_search,
            web_search_context_size=context_size,
            require_exact_source=require_exact_source,
            config_path=path,
            config_sha256=hashlib.sha256(protocol_bytes).hexdigest(),
        )
    if not experiments:
        raise VerificationError("Plik nie definiuje żadnego eksperymentu")
    return experiments
