from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import VerificationError
from .common import canonical_json, read_jsonl, sha256_bytes
from .config import Experiment
from .urls import canonicalize_source_url


def load_questions(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records = read_jsonl(path, "pliku pytań")
    by_id: dict[str, dict[str, Any]] = {}
    required_strings = (
        "id",
        "category",
        "question_pl",
        "gold_answer",
        "reference_passage",
        "source_url",
    )
    for index, record in enumerate(records, start=1):
        for field in required_strings:
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise VerificationError(
                    f"Brak poprawnego pola {field!r} w pytaniu nr {index}"
                )
        question_id = record["id"]
        if question_id in by_id:
            raise VerificationError(f"Powtórzone ID pytania: {question_id}")
        aliases = record.get("accepted_answers")
        if (
            not isinstance(aliases, list)
            or not aliases
            or any(not isinstance(value, str) or not value.strip() for value in aliases)
        ):
            raise VerificationError(
                f"accepted_answers dla {question_id} musi być niepustą listą napisów"
            )
        record["source_url"] = canonicalize_source_url(record["source_url"])
        by_id[question_id] = record
    if not records:
        raise VerificationError(f"Plik pytań jest pusty: {path}")
    return records, by_id


def answer_key(answer: dict[str, Any]) -> tuple[str, str]:
    parameters = answer.get("model_parameters")
    if not isinstance(parameters, dict):
        raise VerificationError(
            f"Brak model_parameters dla odpowiedzi {answer.get('id')!r}"
        )
    model_id = parameters.get("model_id")
    question_id = answer.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise VerificationError(f"Brak model_parameters.model_id dla {question_id!r}")
    if not isinstance(question_id, str) or not question_id.strip():
        raise VerificationError("Odpowiedź bez poprawnego pola id")
    if not isinstance(answer.get("response"), str):
        raise VerificationError(
            f"Pole response dla {model_id} / {question_id} nie jest napisem"
        )
    return model_id, question_id


def load_answers(
    path: Path, questions_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    records = read_jsonl(path, "pliku odpowiedzi")
    seen: set[tuple[str, str]] = set()
    for answer in records:
        key = answer_key(answer)
        if key in seen:
            raise VerificationError(
                f"Powtórzona odpowiedź dla modelu {key[0]} i pytania {key[1]}"
            )
        if key[1] not in questions_by_id:
            raise VerificationError(
                f"Odpowiedź odwołuje się do nieznanego pytania: {key[1]}"
            )
        seen.add(key)
    if not records:
        raise VerificationError(f"Plik odpowiedzi jest pusty: {path}")
    return records


def annotation_input(
    question: dict[str, Any], answer: dict[str, Any], experiment: Experiment
) -> dict[str, Any]:
    available = {
        "question_id": question["id"],
        "category": question["category"],
        "question": question["question_pl"],
        "gold_answer": question["gold_answer"],
        "accepted_answers": question["accepted_answers"],
        "reference_passage": question["reference_passage"],
        "source_url": question["source_url"],
        "model_response": answer["response"],
    }
    value = {field: available[field] for field in experiment.input_fields}
    if tuple(value) != experiment.input_fields:
        raise VerificationError(
            f"Pola wejścia nie odpowiadają protokołowi {experiment.experiment_id}"
        )
    return value


def item_sha256(
    question: dict[str, Any], answer: dict[str, Any], experiment: Experiment
) -> str:
    return sha256_bytes(
        canonical_json(
            {
                "experiment_id": experiment.experiment_id,
                "annotation_input": annotation_input(question, answer, experiment),
                "model_parameters": answer["model_parameters"],
            }
        )
    )


def render_prompt(prompt: str, instance: dict[str, Any]) -> str:
    marker = "{{INSTANCE}}"
    if prompt.count(marker) != 1:
        raise VerificationError(
            f"Prompt musi zawierać dokładnie jeden znacznik {marker}"
        )
    return prompt.replace(marker, json.dumps(instance, ensure_ascii=False, indent=2))


def selected_answers(
    answers: list[dict[str, Any]],
    ids: str | None,
    models: list[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    requested_ids = (
        {value.strip() for value in ids.split(",") if value.strip()} if ids else None
    )
    requested_models = set(models) if models else None
    known_ids = {answer_key(answer)[1] for answer in answers}
    known_models = {answer_key(answer)[0] for answer in answers}
    if requested_ids:
        unknown = sorted(requested_ids - known_ids)
        if unknown:
            raise VerificationError("Nieznane ID pytań: " + ", ".join(unknown))
    if requested_models:
        unknown = sorted(requested_models - known_models)
        if unknown:
            raise VerificationError(
                "Nieznane identyfikatory modeli: " + ", ".join(unknown)
            )
    selected = [
        answer
        for answer in answers
        if (requested_ids is None or answer_key(answer)[1] in requested_ids)
        and (requested_models is None or answer_key(answer)[0] in requested_models)
    ]
    return selected[:limit] if limit is not None else selected
