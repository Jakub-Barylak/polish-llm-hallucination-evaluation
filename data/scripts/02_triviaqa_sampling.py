#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pobranie i przygotowanie kandydatów ``global`` z TriviaQA.

Skrypt wykonuje wyłącznie etap źródłowy: pobiera split ``validation``,
stosuje powtarzalne losowanie i filtry jakościowe, a następnie zapisuje CSV
zgodny z kontraktem ``03_selekcja_pytan.py``. TriviaQA w konfiguracji
``rc.nocontext`` nie zawiera passaży referencyjnych, dlatego pola ``passaz``
i ``passaz_url`` pozostają puste do późniejszego etapu opracowania pytań.

Uruchomienie z katalogu ``repo/data``:

    uv run python scripts/02_triviaqa_sampling.py

Wyjście: ``triviaqa_kandydaci.csv``. Domyślnie powstaje nadmiarowa pula 250
kandydatów, z której generyczny selektor ma wybrać 100 pytań.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = DATA_DIR / "triviaqa_kandydaci.csv"

DATASET_NAME = "mandarjoshi/trivia_qa"
DATASET_CONFIG = "rc.nocontext"
DATASET_SPLIT = "validation"
DEFAULT_POOL_SIZE = 250
DEFAULT_SEED = 42

# Pierwsze siedem pól stanowi wspólny kontrakt generatorów 01 i 02 z
# selektorem 03. Końcowe trzy pola zachowują proweniencję TriviaQA.
CANDIDATE_FIELDS = (
    "zrodlo",
    "qid",
    "pytanie",
    "gold_answer",
    "aliases",
    "passaz",
    "passaz_url",
    "dataset_config",
    "dataset_split",
    "source_question_id",
)

# Sekwencja co najmniej dwóch cudzysłowów jest artefaktem scrapingu.
QUOTE_ARTIFACT_RE = re.compile(r'"{2,}')
STOPWORDS_EN = set(
    """the a an of and or but to in on at by with from as that which who what
    was is were are be been being for nor than then""".split()
)


class TriviaQAError(Exception):
    """Błąd przygotowania kandydatów TriviaQA."""


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def tokens(value: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-zA-Z']+", value.lower())
        if len(word) >= 3 and word not in STOPWORDS_EN
    }


def unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = norm(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def clean_aliases(gold: str, aliases: Iterable[Any]) -> list[str]:
    """Odcina oczywiście skontaminowane aliasy i zawsze zachowuje gold.

    TriviaQA zawiera czasem aliasy z innej encji Wikipedii. Heurystyka
    wspólnego tokenu ogranicza ten problem, lecz ostateczna lista nadal
    wymaga ręcznej kontroli po wybraniu pytania.
    """

    gold_tokens = tokens(gold)
    result = [gold]
    for alias in aliases:
        cleaned = norm(alias)
        if not cleaned:
            continue
        if cleaned.casefold() == gold.casefold() or len(cleaned) <= 3 or not gold_tokens:
            result.append(cleaned)
            continue
        if tokens(cleaned) & gold_tokens:
            result.append(cleaned)
    return unique_strings(result)


def stable_qid(source_qid: Any, question: str) -> str:
    raw = norm(source_qid)
    if raw:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")
        if safe:
            return f"triviaqa_{safe}"
    digest = hashlib.sha1(question.casefold().encode("utf-8")).hexdigest()[:12]
    return f"triviaqa_{digest}"


def build_candidates(
    dataset: Iterable[dict[str, Any]], pool_size: int
) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    seen_qids: set[str] = set()
    seen_questions: set[str] = set()
    stats = {
        "scanned": 0,
        "duplicates": 0,
        "quote_artifacts": 0,
        "invalid_length": 0,
        "missing_data": 0,
    }

    for example in dataset:
        stats["scanned"] += 1
        question = norm(example.get("question", ""))
        answer = example.get("answer", {}) or {}
        if not isinstance(answer, dict):
            answer = {}
        gold = norm(answer.get("value", ""))

        if not question or not gold:
            stats["missing_data"] += 1
            continue
        if len(gold) > 60 or not 12 <= len(question) <= 200:
            stats["invalid_length"] += 1
            continue
        if QUOTE_ARTIFACT_RE.search(question):
            stats["quote_artifacts"] += 1
            continue

        source_id = norm(example.get("question_id", ""))
        qid = stable_qid(source_id, question)
        question_key = question.casefold()
        if qid in seen_qids or question_key in seen_questions:
            stats["duplicates"] += 1
            continue

        raw_aliases = answer.get("aliases", []) or []
        if not isinstance(raw_aliases, (list, tuple)):
            raw_aliases = [raw_aliases]
        aliases = clean_aliases(gold, raw_aliases)
        rows.append(
            {
                "zrodlo": "triviaqa",
                "qid": qid,
                "pytanie": question,
                "gold_answer": gold,
                "aliases": "|".join(aliases),
                "passaz": "",
                "passaz_url": "",
                "dataset_config": DATASET_CONFIG,
                "dataset_split": DATASET_SPLIT,
                "source_question_id": source_id,
            }
        )
        seen_qids.add(qid)
        seen_questions.add(question_key)
        if len(rows) >= pool_size:
            break

    return rows, stats


def atomic_write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("wartość musi być liczbą całkowitą") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("wartość musi być większa od zera")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pobierz i przygotuj pulę kandydatów z TriviaQA."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pool-size", type=positive_int, default=DEFAULT_POOL_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        # Import leniwy ułatwia testowanie filtrów bez biblioteki datasets.
        from datasets import load_dataset

        print(f"Pobieranie {DATASET_NAME} [{DATASET_CONFIG}/{DATASET_SPLIT}] ...")
        dataset = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLIT)
        dataset = dataset.shuffle(seed=args.seed)
        rows, stats = build_candidates(dataset, args.pool_size)
        if len(rows) < args.pool_size:
            raise TriviaQAError(
                f"Po filtracji znaleziono tylko {len(rows)} z wymaganych "
                f"{args.pool_size} kandydatów"
            )
        atomic_write_csv(args.output, rows)
    except (TriviaQAError, OSError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2

    print(f"Przeskanowano:               {stats['scanned']}")
    print(f"Odrzucono duplikatów:        {stats['duplicates']}")
    print(f"Artefakty cudzysłowów:       {stats['quote_artifacts']}")
    print(f"Niepoprawna długość:         {stats['invalid_length']}")
    print(f"Brak pytania lub odpowiedzi: {stats['missing_data']}")
    print(f"Zapisano {len(rows)} kandydatów do {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
