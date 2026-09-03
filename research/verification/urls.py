from __future__ import annotations

import unicodedata
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from . import VerificationError


_PATH_SEGMENT_SAFE = ":@!$&'()*+,;=-._~"
_QUERY_SAFE = "=&?/:@!$'()*+,;~-._"


def _encoded_path(path: str) -> str:
    """Koduje Unicode, nie zamieniając zakodowanego %2F w separator ścieżki."""
    return "/".join(
        quote(
            unicodedata.normalize("NFC", unquote(segment)),
            safe=_PATH_SEGMENT_SAFE,
        )
        for segment in path.split("/")
    )


def _normalized_parts(value: str) -> tuple[str, str, int | None, str, str]:
    parts = urlsplit(value.strip())
    scheme = parts.scheme.casefold()
    host = (parts.hostname or "").casefold().removeprefix("www.")
    if scheme not in {"http", "https"} or not host:
        raise VerificationError(f"Niepoprawny source_url: {value!r}")
    try:
        port = parts.port
    except ValueError as exc:
        raise VerificationError(f"Niepoprawny source_url: {value!r}") from exc
    return scheme, host, port, _encoded_path(parts.path) or "/", parts.query


def canonicalize_source_url(value: str) -> str:
    """Przygotowuje jednoznaczny URL źródła do promptu i wywołania API."""
    parts = urlsplit(value.strip())
    scheme, host, port, path, _ = _normalized_parts(value)

    # Końcowy slash jest częścią ścieżki. Dla artykułu Wikipedii tworzy inny,
    # zwykle nieistniejący tytuł, dlatego naprawiamy go tylko w źródle
    # wejściowym, zanim adres zostanie przekazany modelowi.
    if (
        (host == "wikipedia.org" or host.endswith(".wikipedia.org"))
        and path.startswith("/wiki/")
    ):
        path = path.rstrip("/")

    netloc = parts.hostname or host
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if port is not None:
        netloc = f"{netloc}:{port}"
    query = quote(
        unicodedata.normalize("NFC", unquote(parts.query)),
        safe=_QUERY_SAFE,
    )
    return urlunsplit((scheme, netloc.casefold(), path, query, ""))


def urls_equivalent(actual: str, expected: str) -> bool:
    """Porównuje odwiedzony URL bez naprawiania błędnej ścieżki narzędzia."""
    try:
        actual_parts = _normalized_parts(actual)
        expected_parts = _normalized_parts(canonicalize_source_url(expected))
    except VerificationError:
        return False

    actual_scheme, actual_host, actual_port, actual_path, actual_query = (
        actual_parts
    )
    expected_scheme, expected_host, expected_port, expected_path, expected_query = (
        expected_parts
    )
    same_page = (
        actual_scheme == expected_scheme
        and actual_host == expected_host
        and actual_port == expected_port
        and actual_path == expected_path
    )
    return same_page and (
        not expected_query or actual_query == expected_query
    )
