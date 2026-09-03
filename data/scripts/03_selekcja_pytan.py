#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stanowy selektor pytań ze wspólnego CSV kandydatów.

Skrypt obsługuje dwa sposoby pracy:

* interaktywną sesję człowieka (``review``),
* pojedyncze komendy dla zewnętrznego agenta
  (``next --json``, ``accept``, ``reject``).

Źródłowy CSV nigdy nie jest modyfikowany. Kanoniczną historią pracy jest
append-only ``decyzje.jsonl``. Pliki ``zaakceptowane.jsonl`` i
``odrzucone.jsonl`` są po każdej zmianie odtwarzane z dziennika. Komenda
``export`` pozwala odtworzyć je również na żądanie.

Przykłady:

    python 03_selekcja_pytan.py review
    python 03_selekcja_pytan.py next --json
    python 03_selekcja_pytan.py accept poquad_123 --reviewer agent
    python 03_selekcja_pytan.py reject poquad_456 \
        --reason context_dependent --reviewer agent
    python 03_selekcja_pytan.py stats
    python 03_selekcja_pytan.py undo poquad_456
    python 03_selekcja_pytan.py export

Domyślne ścieżki dotyczą kategorii ``general`` dla zgodności z rozpoczętą
selekcją. Inny zbiór korzysta z tej samej logiki przez ``--input``,
``--output-dir`` i ``--target``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DATA_DIR / "kandydaci_general_pelna_pula.csv"
DEFAULT_OUTPUT_DIR = DATA_DIR / "selekcja_general"
DEFAULT_TARGET = 200
DEFAULT_SEED = 42

REQUIRED_COLUMNS = (
    "zrodlo",
    "qid",
    "pytanie",
    "gold_answer",
    "aliases",
    "passaz",
    "passaz_url",
)
TARGET_FIELDS = (
    "id",
    "category",
    "subcategory",
    "question_pl",
    "gold_answer",
    "accepted_answers",
    "reference_passage",
    "source_url",
    "extraction_date",
)
REJECTION_REASONS = (
    "context_dependent",
    "outside_scope",
    "polish_realia",
    "ambiguous_answer",
    "multiple_answers",
    "malformed_question",
    "unsupported_gold",
    "temporally_unstable",
    "duplicate",
    "not_factual",
    "other",
)


class SelectionError(Exception):
    """Błąd danych lub niedozwolonej operacji selekcji."""


def load_candidates(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        raise SelectionError(f"Nie znaleziono pliku wejściowego: {path}")

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            if fieldnames is None:
                raise SelectionError(f"Plik CSV nie ma nagłówka: {path}")

            missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
            if missing:
                raise SelectionError(
                    "Brak wymaganych kolumn w pliku CSV: " + ", ".join(missing)
                )
            rows = [dict(row) for row in reader]
    except UnicodeDecodeError as exc:
        raise SelectionError(f"Plik wejściowy nie jest poprawnym UTF-8: {path}") from exc
    except csv.Error as exc:
        raise SelectionError(f"Nie można odczytać CSV {path}: {exc}") from exc

    seen: set[str] = set()
    duplicates: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        qid = row.get("qid", "").strip()
        if not qid:
            raise SelectionError(f"Pusty qid w wierszu {row_number} pliku {path}")
        if qid in seen:
            duplicates.add(qid)
        seen.add(qid)
    if duplicates:
        example = ", ".join(sorted(duplicates)[:5])
        raise SelectionError(f"QID nie są unikalne; przykłady: {example}")

    return rows, list(fieldnames)


def candidates_by_qid(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["qid"]: row for row in rows}


def load_events(
    journal_path: Path, known_qids: set[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not journal_path.exists():
        return [], {}
    if not journal_path.is_file():
        raise SelectionError(f"Ścieżka dziennika nie jest plikiem: {journal_path}")

    events: list[dict[str, Any]] = []
    states: dict[str, dict[str, Any]] = {}
    with journal_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise SelectionError(
                    f"Uszkodzony JSON w {journal_path}, linia {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(event, dict):
                raise SelectionError(
                    f"Niepoprawne zdarzenie w {journal_path}, linia {line_number}"
                )

            action = event.get("action")
            qid = event.get("qid")
            if action not in {"accept", "reject", "undo"} or not isinstance(qid, str):
                raise SelectionError(
                    f"Niepoprawne zdarzenie w {journal_path}, linia {line_number}"
                )
            if qid not in known_qids:
                raise SelectionError(
                    f"Dziennik odwołuje się do nieznanego QID {qid!r} "
                    f"w linii {line_number}"
                )
            if action == "reject" and event.get("reason_code") not in REJECTION_REASONS:
                raise SelectionError(
                    f"Niepoprawny powód odrzucenia dla {qid!r} "
                    f"w linii {line_number}"
                )

            events.append(event)
            if action == "undo":
                states.pop(qid, None)
            else:
                states[qid] = event

    return events, states


def ordered_qids(rows: list[dict[str, str]], seed: int) -> list[str]:
    qids = [row["qid"] for row in rows]
    random.Random(seed).shuffle(qids)
    return qids


def progress(states: dict[str, dict[str, Any]], total: int, target: int) -> dict[str, int]:
    accepted = sum(event["action"] == "accept" for event in states.values())
    rejected = sum(event["action"] == "reject" for event in states.values())
    return {
        "accepted": accepted,
        "rejected": rejected,
        "reviewed": accepted + rejected,
        "remaining_unreviewed": total - accepted - rejected,
        "target": target,
        "remaining_to_target": max(target - accepted, 0),
        "total_candidates": total,
    }


def next_candidate(
    rows_by_qid: dict[str, dict[str, str]],
    order: Iterable[str],
    states: dict[str, dict[str, Any]],
    target: int,
) -> tuple[str, dict[str, str] | None]:
    accepted = sum(event["action"] == "accept" for event in states.values())
    if accepted >= target:
        return "complete", None
    for qid in order:
        if qid not in states:
            return "ok", rows_by_qid[qid]
    return "exhausted", None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_event(
    action: str,
    qid: str,
    reviewer: str,
    reason_code: str = "",
    note: str = "",
) -> dict[str, str]:
    return {
        "action": action,
        "qid": qid,
        "reason_code": reason_code,
        "note": note,
        "reviewer": reviewer,
        "timestamp": utc_timestamp(),
    }


def append_event(journal_path: Path, event: dict[str, str]) -> None:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        json.dump(event, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            for row in rows:
                json.dump(row, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def accepted_answers(row: dict[str, str]) -> list[str]:
    """Zwraca gold i aliasy jako unikalną listę w kolejności źródłowej."""
    values = [row["gold_answer"]]
    values.extend(row.get("aliases", "").split("|"))
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def target_record(row: dict[str, str], category: str, index: int) -> dict[str, Any]:
    """Buduje rekord w dziewięciopolowym schemacie ``pytania.jsonl``."""
    record: dict[str, Any] = {
        "id": f"{category}-{index:04d}",
        "category": category,
        "subcategory": "",
        "question_pl": row["pytanie"],
        "gold_answer": row["gold_answer"],
        "accepted_answers": accepted_answers(row),
        "reference_passage": row.get("passaz", ""),
        "source_url": row.get("passaz_url", ""),
        "extraction_date": "",
    }
    assert tuple(record) == TARGET_FIELDS
    return record


def rejected_record(row: dict[str, str], event: dict[str, Any]) -> dict[str, Any]:
    """Buduje audytowy rekord odrzuconego kandydata."""
    return {
        "qid": row["qid"],
        "source": row["zrodlo"],
        "question": row["pytanie"],
        "gold_answer": row["gold_answer"],
        "accepted_answers": accepted_answers(row),
        "reference_passage": row.get("passaz", ""),
        "source_url": row.get("passaz_url", ""),
        "reason_code": str(event.get("reason_code", "")),
        "note": str(event.get("note", "")),
        "reviewer": str(event.get("reviewer", "")),
        "decided_at": str(event.get("timestamp", "")),
    }


def sync_exports(
    output_dir: Path,
    rows_by_qid: dict[str, dict[str, str]],
    states: dict[str, dict[str, Any]],
    order: Iterable[str],
    category: str,
) -> tuple[int, int]:
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for qid in order:
        event = states.get(qid)
        if event is None:
            continue
        if event["action"] == "accept":
            accepted_rows.append(
                target_record(rows_by_qid[qid], category, len(accepted_rows) + 1)
            )
        else:
            rejected_rows.append(rejected_record(rows_by_qid[qid], event))

    atomic_write_jsonl(output_dir / "zaakceptowane.jsonl", accepted_rows)
    atomic_write_jsonl(output_dir / "odrzucone.jsonl", rejected_rows)
    return len(accepted_rows), len(rejected_rows)


def record_decision(
    *,
    action: str,
    qid: str,
    reviewer: str,
    reason_code: str,
    note: str,
    journal_path: Path,
    rows_by_qid: dict[str, dict[str, str]],
    states: dict[str, dict[str, Any]],
    order: list[str],
    output_dir: Path,
    target: int,
    category: str,
) -> dict[str, str]:
    if qid not in rows_by_qid:
        raise SelectionError(f"Nieznany QID: {qid}")
    if qid in states:
        raise SelectionError(
            f"QID {qid} ma już decyzję {states[qid]['action']!r}; najpierw użyj undo"
        )
    if action == "accept":
        current = progress(states, len(rows_by_qid), target)
        if current["accepted"] >= target:
            raise SelectionError(f"Osiągnięto już cel {target} zaakceptowanych pytań")
    if action == "reject" and reason_code not in REJECTION_REASONS:
        raise SelectionError(f"Nieznany powód odrzucenia: {reason_code}")

    event = make_event(action, qid, reviewer, reason_code, note)
    append_event(journal_path, event)
    states[qid] = event
    sync_exports(output_dir, rows_by_qid, states, order, category)
    return event


def undo_decision(
    *,
    qid: str,
    reviewer: str,
    note: str,
    journal_path: Path,
    rows_by_qid: dict[str, dict[str, str]],
    states: dict[str, dict[str, Any]],
    order: list[str],
    output_dir: Path,
    category: str,
) -> dict[str, str]:
    if qid not in rows_by_qid:
        raise SelectionError(f"Nieznany QID: {qid}")
    if qid not in states:
        raise SelectionError(f"QID {qid} nie ma decyzji do cofnięcia")

    event = make_event("undo", qid, reviewer, note=note)
    append_event(journal_path, event)
    states.pop(qid)
    sync_exports(output_dir, rows_by_qid, states, order, category)
    return event


def candidate_payload(
    status: str,
    row: dict[str, str] | None,
    current_progress: dict[str, int],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "progress": current_progress,
    }
    if row is not None:
        payload["record"] = row
    return payload


def print_candidate_human(
    status: str,
    row: dict[str, str] | None,
    current_progress: dict[str, int],
) -> None:
    accepted = current_progress["accepted"]
    target = current_progress["target"]
    if status == "complete":
        print(f"Cel osiągnięty: zaakceptowano {accepted}/{target} pytań.")
        return
    if status == "exhausted":
        print(
            "Brak nieocenionych pytań. "
            f"Zaakceptowano {accepted}/{target}; należy uzupełnić pulę albo cofnąć decyzje."
        )
        return
    assert row is not None
    print("=" * 80)
    print(
        f"QID: {row['qid']} | źródło: {row['zrodlo']} | "
        f"zaakceptowane: {accepted}/{target} | "
        f"ocenione: {current_progress['reviewed']}/{current_progress['total_candidates']}"
    )
    print("-" * 80)
    print(f"PYTANIE:\n{row['pytanie']}")
    print(f"\nGOLD ANSWER:\n{row['gold_answer']}")
    print(f"\nALIASY:\n{row['aliases'] or '(brak)'}")
    if row["passaz"]:
        print(f"\nPASSAŻ REFERENCYJNY:\n{row['passaz']}")
    if row["passaz_url"]:
        print(f"\nURL:\n{row['passaz_url']}")
    print("=" * 80)


def print_progress_human(current_progress: dict[str, int]) -> None:
    print(f"Zaakceptowane:       {current_progress['accepted']}/{current_progress['target']}")
    print(f"Odrzucone:           {current_progress['rejected']}")
    print(f"Łącznie ocenione:    {current_progress['reviewed']}")
    print(f"Nieocenione:         {current_progress['remaining_unreviewed']}")
    print(f"Brakuje do celu:     {current_progress['remaining_to_target']}")
    print(f"Wszystkich w puli:   {current_progress['total_candidates']}")


def choose_rejection_reason() -> str:
    print("Powód odrzucenia:")
    for index, reason in enumerate(REJECTION_REASONS, start=1):
        print(f"  {index:2}. {reason}")
    while True:
        raw = input("Wybierz numer: ").strip()
        try:
            index = int(raw)
        except ValueError:
            print("Podaj numer z listy.")
            continue
        if 1 <= index <= len(REJECTION_REASONS):
            return REJECTION_REASONS[index - 1]
        print("Podaj numer z listy.")


def run_review(
    *,
    rows_by_qid: dict[str, dict[str, str]],
    states: dict[str, dict[str, Any]],
    order: list[str],
    journal_path: Path,
    output_dir: Path,
    target: int,
    reviewer: str,
    category: str,
) -> int:
    while True:
        current_progress = progress(states, len(rows_by_qid), target)
        status, row = next_candidate(rows_by_qid, order, states, target)
        print_candidate_human(status, row, current_progress)
        if status != "ok":
            return 0
        assert row is not None

        while True:
            choice = input("[a] zaakceptuj, [o] odrzuć, [q] zakończ: ").strip().lower()
            if choice in {"a", "o", "r", "q"}:
                break
            print("Nieznana opcja. Wybierz a, o albo q.")
        if choice == "q":
            print("Zapisano dotychczasowy postęp.")
            return 0

        reason = choose_rejection_reason() if choice in {"o", "r"} else ""
        note = input("Opcjonalna notatka (Enter = brak): ").strip()
        action = "accept" if choice == "a" else "reject"
        record_decision(
            action=action,
            qid=row["qid"],
            reviewer=reviewer,
            reason_code=reason,
            note=note,
            journal_path=journal_path,
            rows_by_qid=rows_by_qid,
            states=states,
            order=order,
            output_dir=output_dir,
            target=target,
            category=category,
        )
        print(f"Zapisano decyzję: {action} dla {row['qid']}.\n")


def non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("wartość nie może być pusta")
    return value


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("wartość musi być liczbą całkowitą") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("wartość musi być większa od zera")
    return parsed


def resolve_category(rows: list[dict[str, str]], requested: str) -> str:
    if requested != "auto":
        return requested
    sources = {row["zrodlo"].strip().casefold() for row in rows}
    return "global" if sources == {"triviaqa"} else "general"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interaktywna i agentowa selekcja pytań z CSV do JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Kryterium podstawowe: pytanie musi być samodzielne, faktograficzne, "
            "jednoznaczne i należeć do zakresu wybranego podzbioru. Jeżeli "
            "passaż jest dostępny, służy do weryfikacji gold answer, a nie do "
            "domyślania się podmiotu pytania."
        ),
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="źródłowy CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="katalog dziennika i wynikowych JSONL",
    )
    parser.add_argument("--target", type=positive_int, default=DEFAULT_TARGET)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--category",
        choices=("auto", "general", "global"),
        default="auto",
        help="kategoria i prefiks ID; auto rozpoznaje TriviaQA jako global",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    review = subparsers.add_parser("review", help="uruchom interaktywną pętlę")
    review.add_argument("--reviewer", type=non_empty, default="human")

    next_parser = subparsers.add_parser("next", help="pokaż następne pytanie")
    next_parser.add_argument("--json", action="store_true", help="zwróć maszynowy JSON")

    accept = subparsers.add_parser("accept", help="zaakceptuj pytanie")
    accept.add_argument("qid")
    accept.add_argument("--reviewer", type=non_empty, default="human")
    accept.add_argument("--note", default="")

    reject = subparsers.add_parser("reject", help="odrzuć pytanie")
    reject.add_argument("qid")
    reject.add_argument("--reason", required=True, choices=REJECTION_REASONS)
    reject.add_argument("--reviewer", type=non_empty, default="human")
    reject.add_argument("--note", default="")

    undo = subparsers.add_parser("undo", help="cofnij bieżącą decyzję dla QID")
    undo.add_argument("qid")
    undo.add_argument("--reviewer", type=non_empty, default="human")
    undo.add_argument("--note", default="")

    stats = subparsers.add_parser("stats", help="pokaż postęp selekcji")
    stats.add_argument("--json", action="store_true", help="zwróć maszynowy JSON")

    subparsers.add_parser(
        "export",
        help="odtwórz pliki JSONL z wejściowego CSV i dziennika decyzji",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    journal_path = output_dir / "decyzje.jsonl"

    try:
        rows, _ = load_candidates(input_path)
        category = resolve_category(rows, args.category)
        rows_by_qid = candidates_by_qid(rows)
        _, states = load_events(journal_path, set(rows_by_qid))
        order = ordered_qids(rows, args.seed)

        if args.command == "next":
            current_progress = progress(states, len(rows), args.target)
            status, row = next_candidate(rows_by_qid, order, states, args.target)
            if args.json:
                print(
                    json.dumps(
                        candidate_payload(status, row, current_progress),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print_candidate_human(status, row, current_progress)
            return 0

        if args.command == "stats":
            current_progress = progress(states, len(rows), args.target)
            if args.json:
                print(json.dumps(current_progress, ensure_ascii=False, indent=2))
            else:
                print_progress_human(current_progress)
            return 0

        if args.command == "export":
            accepted, rejected = sync_exports(
                output_dir,
                rows_by_qid,
                states,
                order,
                category,
            )
            print(
                f"Odtworzono zaakceptowane.jsonl ({accepted}) i "
                f"odrzucone.jsonl ({rejected})."
            )
            return 0

        if args.command == "review":
            return run_review(
                rows_by_qid=rows_by_qid,
                states=states,
                order=order,
                journal_path=journal_path,
                output_dir=output_dir,
                target=args.target,
                reviewer=args.reviewer,
                category=category,
            )

        if args.command in {"accept", "reject"}:
            action = args.command
            reason = args.reason if action == "reject" else ""
            record_decision(
                action=action,
                qid=args.qid,
                reviewer=args.reviewer,
                reason_code=reason,
                note=args.note,
                journal_path=journal_path,
                rows_by_qid=rows_by_qid,
                states=states,
                order=order,
                output_dir=output_dir,
                target=args.target,
                category=category,
            )
            current_progress = progress(states, len(rows), args.target)
            print(
                f"Zapisano {action} dla {args.qid}. "
                f"Zaakceptowane: {current_progress['accepted']}/{args.target}."
            )
            return 0

        if args.command == "undo":
            undo_decision(
                qid=args.qid,
                reviewer=args.reviewer,
                note=args.note,
                journal_path=journal_path,
                rows_by_qid=rows_by_qid,
                states=states,
                order=order,
                output_dir=output_dir,
                category=category,
            )
            print(f"Cofnięto decyzję dla {args.qid}.")
            return 0

        raise SelectionError(f"Nieobsługiwana komenda: {args.command}")
    except SelectionError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Błąd operacji na pliku: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nPrzerwano. Dotychczasowy postęp pozostaje zapisany.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
