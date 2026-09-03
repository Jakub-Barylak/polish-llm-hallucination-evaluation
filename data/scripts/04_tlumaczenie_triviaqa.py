#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tłumaczenie zaakceptowanych rekordów TriviaQA do docelowego JSONL.

Wyniki API są archiwizowane append-only. Dzięki odciskowi wejścia i promptu
skrypt może bezpiecznie wznowić pracę bez ponownych wywołań dla już wykonanej
konfiguracji.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DATA_DIR = Path(__file__).resolve().parents[1]
# Wczytaj lokalny plik konfiguracyjny; istniejące zmienne środowiskowe mają
# pierwszeństwo przed wartościami z .env (domyślne zachowanie load_dotenv).
# Plik jest wspólny dla wszystkich skryptów w repozytorium.
load_dotenv(DATA_DIR.parent / ".env")
DEFAULT_INPUT = DATA_DIR / "selekcja_triviaqa" / "zaakceptowane.jsonl"
DEFAULT_OUTPUT = DATA_DIR / "selekcja_triviaqa" / "przetlumaczone.jsonl"
DEFAULT_ARCHIVE = DATA_DIR / "selekcja_triviaqa" / "tlumaczenie" / "surowe_odpowiedzi.jsonl"
DEFAULT_PROMPT = DATA_DIR / "prompts" / "triviaqa_translation_v2.md"
DEFAULT_MODEL = "gpt-4o-2024-11-20"
TEMPERATURE = 0.0
TARGET_FIELDS = (
    "id", "category", "subcategory", "question_pl", "gold_answer",
    "accepted_answers", "reference_passage", "source_url", "extraction_date",
)


class TranslationError(Exception):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise TranslationError(f"Nie znaleziono pliku: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TranslationError(f"Niepoprawny JSON, {path}:{number}: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise TranslationError(f"Rekord {path}:{number} nie jest obiektem JSON")
            rows.append(value)
    ids = [str(row.get("id", "")) for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise TranslationError("Wejściowe rekordy muszą mieć niepuste, unikalne pola id")
    return rows


def json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Nie można zserializować {type(value)!r}")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def config(
    input_bytes: bytes,
    prompt_bytes: bytes,
    model: str,
    prompt_path: Path,
) -> dict[str, Any]:
    return {"model": model, "temperature": TEMPERATURE,
            "input_sha256": sha256_bytes(input_bytes),
            "prompt_sha256": sha256_bytes(prompt_bytes),
            "prompt_version": prompt_path.stem}


def archive_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TranslationError(f"Niepoprawny JSON w archiwum, linia {number}: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise TranslationError(f"Wpis archiwum w linii {number} nie jest obiektem JSON")
            rows.append(value)
    return rows


def successful_by_id(archive: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in archive:
        if event.get("status") == "ok" and event.get("config") == cfg and isinstance(event.get("translation"), dict):
            result[str(event.get("id"))] = event
    return result


def parse_translation(content: str) -> dict[str, Any]:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I)
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TranslationError(f"API nie zwróciło poprawnego JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise TranslationError("Odpowiedź API nie jest obiektem JSON")
    question = value.get("question_pl")
    gold = value.get("gold_answer")
    aliases = value.get("accepted_answers")
    subcategory = value.get("subcategory")
    if not all(isinstance(x, str) and x.strip() for x in (question, gold, subcategory)):
        raise TranslationError("Brak poprawnych pól question_pl, gold_answer lub subcategory")
    if not isinstance(aliases, list) or not aliases or any(not isinstance(x, str) or not x.strip() for x in aliases):
        raise TranslationError("accepted_answers musi być niepustą listą napisów")
    aliases = list(dict.fromkeys(x.strip() for x in aliases))
    if gold.strip().casefold() not in {x.casefold() for x in aliases}:
        aliases.insert(0, gold.strip())
    return {"question_pl": question.strip(), "gold_answer": gold.strip(),
            "accepted_answers": aliases, "subcategory": subcategory.strip()}


def make_record(source: dict[str, Any], translation: dict[str, Any]) -> dict[str, Any]:
    return {"id": source["id"], "category": "global",
            "subcategory": translation["subcategory"],
            "question_pl": translation["question_pl"],
            "gold_answer": translation["gold_answer"],
            "accepted_answers": translation["accepted_answers"],
            "reference_passage": source.get("reference_passage", "") or "",
            "source_url": source.get("source_url", "") or "",
            "extraction_date": source.get("extraction_date", "") or ""}


def build_messages(prompt: str, source: dict[str, Any]) -> list[dict[str, str]]:
    rendered = prompt.replace("{{RECORD}}", json.dumps(source, ensure_ascii=False, indent=2))
    return [{"role": "user", "content": rendered}]


def translate(args: argparse.Namespace) -> int:
    try:
        source_bytes = args.input.read_bytes()
        prompt_bytes = args.prompt.read_bytes()
        sources = read_jsonl(args.input)
        cfg = config(source_bytes, prompt_bytes, args.model, args.prompt)
        archive = archive_records(args.archive)
        done = {} if args.force else successful_by_id(archive, cfg)
        requested = set(args.ids.split(",")) if args.ids else None
        if requested:
            known_ids = {str(row["id"]) for row in sources}
            unknown = sorted(requested - known_ids)
            if unknown:
                raise TranslationError("Nieznane ID rekordów: " + ", ".join(unknown))
        selected = [row for row in sources if requested is None or str(row["id"]) in requested]
        if args.limit:
            selected = selected[:args.limit]
        missing = [row for row in selected if str(row["id"]) not in done]
        print(f"Wybrano {len(selected)} rekordów; do wykonania: {len(missing)}.")
        if missing:
            if not os.environ.get("OPENAI_API_KEY"):
                raise TranslationError("Brak OPENAI_API_KEY")
            from openai import OpenAI
            client = OpenAI()
            prompt = prompt_bytes.decode("utf-8")
            for index, source in enumerate(missing, 1):
                record_id = str(source["id"])
                messages = build_messages(prompt, source)
                try:
                    response = client.chat.completions.create(
                        model=args.model, messages=messages, temperature=TEMPERATURE,
                        response_format={"type": "json_object"}, max_tokens=700,
                    )
                    raw = json.dumps(response, default=json_default, ensure_ascii=False)
                    content = response.choices[0].message.content or ""
                    translation = parse_translation(content)
                    event = {"timestamp": timestamp(), "status": "ok", "id": record_id,
                             "config": cfg, "request": {"model": args.model, "messages": messages,
                             "temperature": TEMPERATURE, "response_format": {"type": "json_object"}},
                             "response": json.loads(raw), "translation": translation}
                    append_jsonl(args.archive, event)
                    done[record_id] = event
                    print(f"[{index}/{len(missing)}] OK {record_id}")
                except Exception as exc:
                    append_jsonl(args.archive, {"timestamp": timestamp(), "status": "error", "id": record_id,
                                                "config": cfg, "request": {"model": args.model, "messages": messages},
                                                "error": repr(exc)})
                    print(f"[{index}/{len(missing)}] BŁĄD {record_id}: {exc}", file=sys.stderr)
        export_records(sources, args.output, args.archive, cfg)
        return 0
    except (OSError, UnicodeDecodeError, TranslationError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2


def export_records(sources: list[dict[str, Any]], output: Path, archive_path: Path, cfg: dict[str, Any]) -> int:
    done = successful_by_id(archive_records(archive_path), cfg)
    records = [make_record(source, done[str(source["id"])] ["translation"])
               for source in sources if str(source["id"]) in done]
    atomic_write_jsonl(output, records)
    print(f"Zapisano {len(records)} rekordów do {output}.")
    return len(records)


def stats(args: argparse.Namespace) -> int:
    archive = archive_records(args.archive)
    statuses: dict[str, int] = {}
    for event in archive:
        statuses[event.get("status", "unknown")] = statuses.get(event.get("status", "unknown"), 0) + 1
    print(json.dumps({"events": len(archive), "statuses": statuses}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    sub = parser.add_subparsers(dest="command", required=True)
    translate_parser = sub.add_parser("translate")
    translate_parser.add_argument("--limit", type=int)
    translate_parser.add_argument("--ids", help="ID-y rozdzielone przecinkami")
    translate_parser.add_argument("--force", action="store_true")
    sub.add_parser("export")
    sub.add_parser("stats")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stats":
        return stats(args)
    if args.command == "export":
        try:
            sources = read_jsonl(args.input)
            cfg = config(
                args.input.read_bytes(),
                args.prompt.read_bytes(),
                args.model,
                args.prompt,
            )
            export_records(sources, args.output, args.archive, cfg)
            return 0
        except (OSError, UnicodeDecodeError, TranslationError) as exc:
            print(f"Błąd: {exc}", file=sys.stderr)
            return 2
    return translate(args)


if __name__ == "__main__":
    raise SystemExit(main())
