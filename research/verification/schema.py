from __future__ import annotations

import json
from typing import Any

from . import VerificationError


LABELS = ("correct", "hallucination", "abstention")
RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "silver_annotation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "label": {"type": "string", "enum": list(LABELS)},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "matched_answer": {
                    "anyOf": [{"type": "string"}, {"type": "null"}]
                },
                "false_claims": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "analysis",
                "label",
                "confidence",
                "matched_answer",
                "false_claims",
            ],
            "additionalProperties": False,
        },
    },
}


def responses_text_format() -> dict[str, Any]:
    schema = RESPONSE_FORMAT["json_schema"]
    return {
        "type": "json_schema",
        "name": schema["name"],
        "strict": schema["strict"],
        "schema": schema["schema"],
    }


def parse_annotation(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VerificationError(
            f"Annotator nie zwrócił poprawnego JSON: {exc.msg}"
        ) from exc
    expected = {
        "analysis",
        "label",
        "confidence",
        "matched_answer",
        "false_claims",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise VerificationError("Odpowiedź annotatora ma niepoprawny zestaw pól")

    analysis = value["analysis"]
    label = value["label"]
    confidence = value["confidence"]
    matched_answer = value["matched_answer"]
    false_claims = value["false_claims"]
    if not isinstance(analysis, str) or not analysis.strip():
        raise VerificationError("Pole analysis musi być niepustym napisem")
    if label not in LABELS:
        raise VerificationError(f"Nieznana etykieta annotatora: {label!r}")
    if (
        not isinstance(confidence, int)
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 100
    ):
        raise VerificationError("Pole confidence musi być liczbą całkowitą 0–100")
    if matched_answer is not None and (
        not isinstance(matched_answer, str) or not matched_answer.strip()
    ):
        raise VerificationError("matched_answer musi być napisem albo null")
    if not isinstance(false_claims, list) or any(
        not isinstance(claim, str) or not claim.strip() for claim in false_claims
    ):
        raise VerificationError("false_claims musi być listą niepustych napisów")
    if label == "hallucination" and not false_claims:
        raise VerificationError("Halucynacja musi zawierać co najmniej jeden false_claim")
    if label != "hallucination" and false_claims:
        raise VerificationError("Tylko hallucination może zawierać false_claims")
    if label == "correct" and matched_answer is None:
        raise VerificationError("Poprawna odpowiedź musi zawierać matched_answer")
    if label == "abstention" and matched_answer is not None:
        raise VerificationError("Abstencja nie może zawierać matched_answer")

    return {
        "analysis": analysis.strip(),
        "label": label,
        "confidence": confidence,
        "matched_answer": matched_answer.strip() if matched_answer else None,
        "false_claims": [claim.strip() for claim in false_claims],
    }


def json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Nie można zserializować obiektu {type(value)!r}")
