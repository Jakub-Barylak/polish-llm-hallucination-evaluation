from __future__ import annotations

import json
import re
import threading
import time
from typing import Any
from urllib.parse import urlsplit

from . import VerificationError
from .config import Experiment
from .schema import (
    RESPONSE_FORMAT,
    json_default,
    parse_annotation,
    responses_text_format,
)
from .urls import canonicalize_source_url, urls_equivalent


class AnnotationValidationError(VerificationError):
    """Błąd treści annotatora z zachowaną płatną odpowiedzią API."""

    def __init__(self, message: str, api_data: dict[str, Any]) -> None:
        super().__init__(message)
        self.api_data = api_data


class RateLimitCoordinator:
    """Koordynuje ponowienia wielu workerów po HTTP 429."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._blocked_until = 0.0
        self._next_request_at = 0.0
        self._minimum_interval = 0.0

    def wait_until_allowed(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                delay = max(self._blocked_until, self._next_request_at) - now
                if delay <= 0:
                    self._next_request_at = now + self._minimum_interval
                    return
            time.sleep(delay)

    def block_for(self, delay_seconds: float) -> float:
        retry_interval = max(delay_seconds, 0.1)
        blocked_until = time.monotonic() + retry_interval + 0.5
        with self._lock:
            self._minimum_interval = max(self._minimum_interval, retry_interval)
            self._blocked_until = max(self._blocked_until, blocked_until)
            self._next_request_at = max(self._next_request_at, self._blocked_until)
            return max(0.0, self._blocked_until - time.monotonic())


def _parse_duration_seconds(value: str) -> float | None:
    value = value.strip().casefold()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|m|min|mins)", value)
    if not matches:
        return None
    multiplier = {
        "ms": 0.001,
        "s": 1.0,
        "sec": 1.0,
        "secs": 1.0,
        "m": 60.0,
        "min": 60.0,
        "mins": 60.0,
    }
    return sum(float(number) * multiplier[unit] for number, unit in matches)


def _retry_after_seconds(error: Exception, retry_number: int) -> float:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        retry_after_ms = headers.get("retry-after-ms")
        if retry_after_ms:
            try:
                return max(0.1, float(retry_after_ms) / 1000)
            except (TypeError, ValueError):
                pass
        for name in ("retry-after", "x-ratelimit-reset-tokens"):
            header_value = headers.get(name)
            if header_value:
                parsed = _parse_duration_seconds(str(header_value))
                if parsed is not None:
                    return max(0.1, parsed)
    match = re.search(
        r"try again in\s+(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|m|min|mins)",
        str(error),
        flags=re.IGNORECASE,
    )
    if match:
        parsed = _parse_duration_seconds("".join(match.groups()))
        if parsed is not None:
            return max(0.1, parsed)
    return min(60.0, float(2 ** min(retry_number, 6)))


def _is_retryable_rate_limit(error: Exception) -> bool:
    if getattr(error, "status_code", None) != 429 and (
        error.__class__.__name__ != "RateLimitError"
    ):
        return False
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested_error = body.get("error")
        details = nested_error if isinstance(nested_error, dict) else body
        if details.get("code") == "insufficient_quota":
            return False
    return "insufficient_quota" not in str(error).casefold()


def _source_domain(source_url: str) -> str:
    domain = urlsplit(source_url).hostname
    if not domain:
        raise VerificationError(f"Niepoprawny source_url: {source_url!r}")
    return domain


def build_request_data(
    *,
    experiment: Experiment,
    model: str,
    rendered_prompt: str,
    source_url: str | None,
) -> dict[str, Any]:
    if experiment.api_endpoint == "chat_completions":
        return {
            "model": model,
            "messages": [{"role": "user", "content": rendered_prompt}],
            "temperature": experiment.temperature,
            "max_completion_tokens": experiment.max_output_tokens,
            "response_format": RESPONSE_FORMAT,
        }

    request: dict[str, Any] = {
        "model": model,
        "input": [{"role": "user", "content": rendered_prompt}],
        "reasoning": {"effort": experiment.reasoning_effort},
        "max_output_tokens": experiment.max_output_tokens,
        "text": {"format": responses_text_format()},
        "store": False,
    }
    if experiment.web_search:
        if not source_url:
            raise VerificationError("Protokół source-web wymaga source_url")
        request.update(
            {
                "tools": [
                    {
                        "type": "web_search",
                        "search_context_size": experiment.web_search_context_size,
                        "filters": {
                            "allowed_domains": [_source_domain(source_url)],
                        },
                    }
                ],
                "tool_choice": "required",
                "include": ["web_search_call.action.sources"],
            }
        )
    return request


def build_batch_request(
    *,
    custom_id: str,
    experiment: Experiment,
    model: str,
    rendered_prompt: str,
    source_url: str | None,
) -> dict[str, Any]:
    """Buduje pojedynczą linię pliku wejściowego OpenAI Batch API."""
    if not custom_id or len(custom_id) > 64:
        raise VerificationError("Batch custom_id musi mieć od 1 do 64 znaków")
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": batch_endpoint(experiment),
        "body": build_request_data(
            experiment=experiment,
            model=model,
            rendered_prompt=rendered_prompt,
            source_url=source_url,
        ),
    }


def batch_endpoint(experiment: Experiment) -> str:
    return {
        "responses": "/v1/responses",
        "chat_completions": "/v1/chat/completions",
    }[experiment.api_endpoint]


def response_text(raw_response: dict[str, Any], api_endpoint: str) -> str:
    """Wyciąga tekst annotatora z surowej odpowiedzi zwykłej lub Batch API."""
    if api_endpoint == "chat_completions":
        choices = raw_response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        return content if isinstance(content, str) else ""

    direct = raw_response.get("output_text")
    if isinstance(direct, str):
        return direct
    texts: list[str] = []
    output = raw_response.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])
    return "".join(texts)


def web_search_audit(
    raw_response: dict[str, Any], expected_source_url: str
) -> dict[str, Any]:
    expected_source_url = canonicalize_source_url(expected_source_url)
    sources: list[dict[str, Any]] = []
    visited_urls: list[dict[str, str]] = []
    calls = 0
    output = raw_response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "web_search_call":
                continue
            calls += 1
            action = item.get("action")
            if not isinstance(action, dict):
                continue
            action_type = action.get("type")
            action_url = action.get("url")
            if isinstance(action_type, str) and isinstance(action_url, str):
                visited_urls.append({"action": action_type, "url": action_url})
            action_sources = action.get("sources")
            if isinstance(action_sources, list):
                sources.extend(x for x in action_sources if isinstance(x, dict))
    candidate_urls = (
        source.get("url") for source in [*sources, *visited_urls]
    )
    consulted = any(
        isinstance(url, str) and urls_equivalent(url, expected_source_url)
        for url in candidate_urls
    )
    return {
        "calls": calls,
        "expected_source_url": expected_source_url,
        "expected_source_consulted": consulted,
        "sources": sources,
        "visited_urls": visited_urls,
    }


def request_annotation(
    client: Any,
    experiment: Experiment,
    model: str,
    rendered_prompt: str,
    source_url: str | None,
    model_id: str,
    question_id: str,
    max_retries: int,
    rate_limit: RateLimitCoordinator,
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = build_request_data(
        experiment=experiment,
        model=model,
        rendered_prompt=rendered_prompt,
        source_url=source_url,
    )
    response: Any = None
    for retry_number in range(max_retries + 1):
        rate_limit.wait_until_allowed()
        try:
            if experiment.api_endpoint == "chat_completions":
                response = client.chat.completions.create(**request)
            else:
                response = client.responses.create(**request)
            break
        except Exception as exc:
            if not _is_retryable_rate_limit(exc) or retry_number >= max_retries:
                raise
            delay = rate_limit.block_for(
                _retry_after_seconds(exc, retry_number + 1)
            )
            print(
                f"[RATE LIMIT] {model_id} / {question_id}: "
                f"ponowienie {retry_number + 1}/{max_retries} za {delay:.1f} s.",
                flush=True,
            )
    if response is None:
        raise VerificationError("Brak odpowiedzi API po zakończeniu ponowień")
    raw_response = json.loads(
        json.dumps(response, default=json_default, ensure_ascii=False)
    )
    api_data: dict[str, Any] = {"request": request, "response": raw_response}
    if experiment.web_search:
        if source_url is None:
            raise VerificationError("Brak source_url w audycie web search")
        api_data["web_search_audit"] = web_search_audit(raw_response, source_url)
    content = response_text(raw_response, experiment.api_endpoint)
    if not content:
        raise AnnotationValidationError(
            "Odpowiedź API nie zawiera treści annotatora", api_data
        )
    try:
        annotation = parse_annotation(content)
    except VerificationError as exc:
        raise AnnotationValidationError(str(exc), api_data) from exc
    return annotation, api_data
