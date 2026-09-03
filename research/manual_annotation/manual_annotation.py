#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Losowanie próby i interaktywna ręczna ocena odpowiedzi modeli.

Kanoniczną historią pracy są dzienniki zdarzeń JSONL. Cofnięcie decyzji dopisuje
zdarzenie ``undo`` i nie usuwa wcześniejszego wpisu. Pliki z bieżącymi ocenami
są po każdej zmianie odtwarzane atomowo z dziennika.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import uuid
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


MANUAL_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = MANUAL_DIR.parent
REPO_DIR = RESEARCH_DIR.parent
DEFAULT_QUESTIONS = REPO_DIR / "data" / "pytania_all.jsonl"
DEFAULT_ANSWERS = RESEARCH_DIR / "odpowiedzi.jsonl"
DEFAULT_ARTIFACTS_DIR = MANUAL_DIR / "artifacts"
GUIDELINES_PATH = MANUAL_DIR / "guidelines.md"

SCHEMA_VERSION = 1
GUIDELINE_VERSION = "manual-validation-v1"
DEFAULT_SEED = 20260818
DEFAULT_CATEGORY_COUNTS = {
    "general": 60,
    "polish_realia": 60,
    "global": 30,
}
EXPECTED_MODELS = 4
LABELS = ("correct", "hallucination", "abstention")
LABEL_SHORTCUTS = {
    "c": "correct",
    "1": "correct",
    "h": "hallucination",
    "2": "hallucination",
    "a": "abstention",
    "3": "abstention",
}
REVIEWER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

PREPARED_FILES = (
    "metadata.json",
    "private_manifest.jsonl",
    "tasks.jsonl",
)

SHORT_GUIDELINES = """\
correct       — odpowiedź jest zgodna z faktami i nie zawiera fałszywego dodatku
hallucination — odpowiedź zawiera sprawdzalne fałszywe twierdzenie
abstention    — brak sprawdzalnej próby odpowiedzi
Niepewna, ale konkretna odpowiedź nie jest abstencją: oceń jej prawdziwość.
"""


class ManualAnnotationError(Exception):
    """Błąd danych, konfiguracji albo niedozwolonej operacji."""


def configure_output_encoding() -> None:
    """Zapobiega awarii na znakach spoza lokalnej strony kodowej Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (LookupError, OSError):
                pass


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise ManualAnnotationError(f"Nie można odczytać {path}: {exc}") from exc


def read_jsonl(path: Path, description: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ManualAnnotationError(f"Nie znaleziono {description}: {path}")
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ManualAnnotationError(
                        f"Niepoprawny JSON w {path}, linia {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(value, dict):
                    raise ManualAnnotationError(
                        f"{path}, linia {line_number}: oczekiwano obiektu JSON"
                    )
                rows.append(value)
    except UnicodeDecodeError as exc:
        raise ManualAnnotationError(f"Plik nie jest poprawnym UTF-8: {path}") from exc
    except OSError as exc:
        raise ManualAnnotationError(f"Nie można odczytać {path}: {exc}") from exc
    return rows


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            for row in rows:
                json.dump(row, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        json.dump(row, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def required_text(row: dict[str, Any], field: str, context: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManualAnnotationError(f"{context}: brak poprawnego pola {field!r}")
    return value.strip()


def load_questions(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = read_jsonl(path, "pliku pytań")
    by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        context = f"{path}, rekord {index}"
        question_id = required_text(row, "id", context)
        for field in (
            "category",
            "question_pl",
            "gold_answer",
            "reference_passage",
            "source_url",
        ):
            required_text(row, field, context)
        aliases = row.get("accepted_answers")
        if (
            not isinstance(aliases, list)
            or not aliases
            or any(not isinstance(value, str) or not value.strip() for value in aliases)
        ):
            raise ManualAnnotationError(
                f"{context}: accepted_answers musi być niepustą listą napisów"
            )
        if question_id in by_id:
            raise ManualAnnotationError(f"Powtórzone ID pytania: {question_id}")
        by_id[question_id] = row
    if not rows:
        raise ManualAnnotationError(f"Plik pytań jest pusty: {path}")
    return rows, by_id


def answer_key(row: dict[str, Any], context: str) -> tuple[str, str]:
    question_id = required_text(row, "id", context)
    parameters = row.get("model_parameters")
    if not isinstance(parameters, dict):
        raise ManualAnnotationError(f"{context}: brak model_parameters")
    model_id = required_text(parameters, "model_id", f"{context}.model_parameters")
    if not isinstance(row.get("response"), str):
        raise ManualAnnotationError(f"{context}: response nie jest napisem")
    return model_id, question_id


def load_answers(
    path: Path,
    questions_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    rows = read_jsonl(path, "pliku odpowiedzi")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    question_models: dict[str, set[str]] = {
        question_id: set() for question_id in questions_by_id
    }
    for index, row in enumerate(rows, start=1):
        key = answer_key(row, f"{path}, rekord {index}")
        if key in by_key:
            raise ManualAnnotationError(
                f"Powtórzona odpowiedź dla modelu {key[0]} i pytania {key[1]}"
            )
        if key[1] not in questions_by_id:
            raise ManualAnnotationError(
                f"Odpowiedź odwołuje się do nieznanego pytania: {key[1]}"
            )
        by_key[key] = row
        question_models[key[1]].add(key[0])

    models = sorted({key[0] for key in by_key})
    if len(models) != EXPECTED_MODELS:
        raise ManualAnnotationError(
            f"Oczekiwano {EXPECTED_MODELS} modeli, znaleziono {len(models)}: {models}"
        )
    expected = set(models)
    invalid = [
        question_id
        for question_id, present in question_models.items()
        if present != expected
    ]
    if invalid:
        raise ManualAnnotationError(
            "Nie każde pytanie ma odpowiedź wszystkich modeli; przykłady: "
            + ", ".join(invalid[:5])
        )
    expected_count = len(questions_by_id) * len(models)
    if len(by_key) != expected_count:
        raise ManualAnnotationError(
            f"Oczekiwano {expected_count} odpowiedzi, znaleziono {len(by_key)}"
        )
    return by_key, models


def select_primary_questions(
    questions: Sequence[dict[str, Any]],
    category_counts: dict[str, int],
    seed: int,
) -> tuple[list[str], dict[str, float]]:
    by_category: dict[str, list[str]] = {}
    for row in questions:
        category = str(row["category"])
        by_category.setdefault(category, []).append(str(row["id"]))

    unknown = sorted(set(category_counts) - set(by_category))
    if unknown:
        raise ManualAnnotationError(
            "W konfiguracji występują nieznane kategorie: " + ", ".join(unknown)
        )
    extra = sorted(set(by_category) - set(category_counts))
    if extra:
        raise ManualAnnotationError(
            "Brak liczebności próby dla kategorii: " + ", ".join(extra)
        )

    rng = random.Random(seed)
    selected: list[str] = []
    probabilities: dict[str, float] = {}
    for category in sorted(category_counts):
        population = sorted(by_category[category])
        count = category_counts[category]
        if count <= 0 or count > len(population):
            raise ManualAnnotationError(
                f"Niepoprawna liczebność {count} dla kategorii {category}; "
                f"dostępnych pytań: {len(population)}"
            )
        chosen = rng.sample(population, count)
        selected.extend(chosen)
        probability = count / len(population)
        probabilities.update({question_id: probability for question_id in chosen})
    return selected, probabilities


def stable_item_id(seed: int, key: tuple[str, str]) -> str:
    payload = f"{GUIDELINE_VERSION}\0{seed}\0{key[0]}\0{key[1]}".encode("utf-8")
    return "mv-" + hashlib.sha256(payload).hexdigest()[:16]


def task_record(item_id: str, question: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_item_id": item_id,
        "question": question["question_pl"],
        "model_response": answer["response"],
        "gold_answer": question["gold_answer"],
        "accepted_answers": question["accepted_answers"],
        "reference_passage": question["reference_passage"],
        "source_url": question["source_url"],
        "extraction_date": question.get("extraction_date") or None,
        "guideline_version": GUIDELINE_VERSION,
    }


def spread_tasks(rows: Sequence[dict[str, Any]], seed: str) -> list[dict[str, Any]]:
    """Losuje kolejność bez sąsiadujących odpowiedzi na to samo pytanie."""
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(str(row["question_id"]), []).append(dict(row))
    for values in buckets.values():
        rng.shuffle(values)

    result: list[dict[str, Any]] = []
    previous: str | None = None
    while buckets:
        candidates = [question_id for question_id in buckets if question_id != previous]
        if not candidates:
            candidates = list(buckets)
        question_id = rng.choice(candidates)
        result.append(buckets[question_id].pop())
        if not buckets[question_id]:
            del buckets[question_id]
        previous = question_id
    return result


def _ensure_prepare_target(artifacts_dir: Path, force: bool) -> None:
    existing = [artifacts_dir / name for name in PREPARED_FILES if (artifacts_dir / name).exists()]
    annotations_dir = artifacts_dir / "annotations"
    has_annotations = annotations_dir.exists() and any(annotations_dir.iterdir())
    if has_annotations:
        raise ManualAnnotationError(
            f"{annotations_dir} zawiera już oceny. Użyj nowego katalogu artefaktów; "
            "próby z rozpoczętą oceną nie wolno nadpisywać."
        )
    if existing and not force:
        raise ManualAnnotationError(
            "Katalog zawiera przygotowaną próbę. Użyj --force tylko przed "
            "rozpoczęciem ocen albo wskaż nowy --artifacts-dir."
        )


def prepare(args: argparse.Namespace) -> int:
    questions_path = args.questions.resolve()
    answers_path = args.answers.resolve()
    artifacts_dir = args.artifacts_dir.resolve()
    _ensure_prepare_target(artifacts_dir, args.force)

    questions, questions_by_id = load_questions(questions_path)
    answers_by_key, models = load_answers(answers_path, questions_by_id)
    universe = set(answers_by_key)

    category_counts = {
        "general": args.general,
        "polish_realia": args.polish_realia,
        "global": args.global_count,
    }
    primary_question_ids, probabilities = select_primary_questions(
        questions, category_counts, args.seed
    )
    primary_questions = set(primary_question_ids)
    selected_keys = {key for key in universe if key[1] in primary_questions}

    private_rows: list[dict[str, Any]] = []
    public_rows_with_question: list[dict[str, Any]] = []
    ids_seen: set[str] = set()
    for key in sorted(selected_keys):
        model_id, question_id = key
        item_id = stable_item_id(args.seed, key)
        if item_id in ids_seen:
            raise ManualAnnotationError(f"Kolizja ślepego identyfikatora: {item_id}")
        ids_seen.add(item_id)
        question = questions_by_id[question_id]
        answer = answers_by_key[key]
        private_rows.append(
            {
                "validation_item_id": item_id,
                "question_id": question_id,
                "model_id": model_id,
                "category": question["category"],
                "question_inclusion_probability": probabilities[question_id],
                "response_sha256": sha256_bytes(str(answer["response"]).encode("utf-8")),
            }
        )
        public_rows_with_question.append(
            {
                **task_record(item_id, question, answer),
                "question_id": question_id,
            }
        )

    ordered_public = spread_tasks(
        public_rows_with_question,
        f"{args.seed}:sample-task-order",
    )
    public_rows = [
        {key: value for key, value in row.items() if key != "question_id"}
        for row in ordered_public
    ]

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "guideline_version": GUIDELINE_VERSION,
        "generated_at": utc_timestamp(),
        "seed": args.seed,
        "category_question_counts": category_counts,
        "models_count": len(models),
        "population_questions": len(questions_by_id),
        "population_answers": len(answers_by_key),
        "sample_questions": len(primary_questions),
        "sample_answers": len(selected_keys),
        "input_paths": {
            "questions": str(questions_path),
            "answers": str(answers_path),
        },
        "input_sha256": {
            "questions": sha256_file(questions_path),
            "answers": sha256_file(answers_path),
            "guidelines": sha256_file(GUIDELINES_PATH),
        },
        "manifest_sha256": sha256_bytes(canonical_json(private_rows)),
    }

    atomic_write_jsonl(artifacts_dir / "private_manifest.jsonl", private_rows)
    atomic_write_jsonl(artifacts_dir / "tasks.jsonl", public_rows)
    atomic_write_json(artifacts_dir / "metadata.json", metadata)

    print(f"Przygotowano próbę w: {artifacts_dir}")
    print(
        f"Próba: {metadata['sample_questions']} pytań / "
        f"{metadata['sample_answers']} odpowiedzi"
    )
    print("Nazwy modeli i etykiety silver nie zostały zapisane w tasks.jsonl.")
    return 0


def validate_reviewer(value: str) -> str:
    value = value.strip()
    if not REVIEWER_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "identyfikator oceniającego: 1–64 znaków A-Z, a-z, 0-9, _ lub -"
        )
    return value


def load_metadata(artifacts_dir: Path) -> dict[str, Any]:
    path = artifacts_dir / "metadata.json"
    if not path.is_file():
        raise ManualAnnotationError(
            f"Brak przygotowanej próby: {path}. Najpierw uruchom prepare."
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManualAnnotationError(f"Nie można odczytać metadanych {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ManualAnnotationError(f"Nieobsługiwana wersja metadanych: {path}")
    return value


def load_task_set(
    artifacts_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    task_name = "tasks.jsonl"
    manifest_name = "private_manifest.jsonl"
    tasks = read_jsonl(artifacts_dir / task_name, "pliku z zadaniami")
    manifest_rows = read_jsonl(artifacts_dir / manifest_name, "prywatnego manifestu")
    manifest = {str(row.get("validation_item_id")): row for row in manifest_rows}
    if len(manifest) != len(manifest_rows):
        raise ManualAnnotationError(f"Powtórzone identyfikatory w {manifest_name}")
    for task in tasks:
        item_id = required_text(task, "validation_item_id", task_name)
        if item_id not in manifest:
            raise ManualAnnotationError(f"Zadanie {item_id} nie występuje w manifeście")
    if len(tasks) != len(manifest):
        raise ManualAnnotationError(
            f"Liczba zadań ({len(tasks)}) nie zgadza się z manifestem ({len(manifest)})"
        )
    return tasks, manifest


def annotation_paths(
    artifacts_dir: Path,
    reviewer: str,
) -> tuple[Path, Path]:
    directory = artifacts_dir / "annotations"
    return (
        directory / f"{reviewer}.events.jsonl",
        directory / f"{reviewer}.jsonl",
    )


def load_events(
    path: Path,
    known_item_ids: set[str],
    reviewer: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not path.exists():
        return [], {}
    rows = read_jsonl(path, "dziennika ocen")
    states: dict[str, dict[str, Any]] = {}
    seen_events: set[str] = set()
    for line_number, event in enumerate(rows, start=1):
        event_id = event.get("event_id")
        item_id = event.get("validation_item_id")
        action = event.get("action")
        if not isinstance(event_id, str) or not event_id or event_id in seen_events:
            raise ManualAnnotationError(f"Niepoprawne event_id w {path}, wpis {line_number}")
        seen_events.add(event_id)
        if item_id not in known_item_ids:
            raise ManualAnnotationError(
                f"Dziennik {path} odwołuje się do nieznanego zadania {item_id!r}"
            )
        if event.get("reviewer") != reviewer:
            raise ManualAnnotationError(f"Dziennik {path} zawiera wpis innego oceniającego")
        if action == "label":
            if event.get("label") not in LABELS:
                raise ManualAnnotationError(f"Niepoprawna etykieta w {path}, wpis {line_number}")
            states[str(item_id)] = event
        elif action == "undo":
            if item_id not in states:
                raise ManualAnnotationError(
                    f"Cofnięcie zadania bez aktywnej oceny w {path}, wpis {line_number}"
                )
            states.pop(str(item_id))
        else:
            raise ManualAnnotationError(f"Niepoprawna akcja w {path}, wpis {line_number}")
    return rows, states


def make_label_event(
    item_id: str,
    reviewer: str,
    label: str,
    comment: str,
    evidence_url: str,
) -> dict[str, Any]:
    if label not in LABELS:
        raise ManualAnnotationError(f"Nieznana etykieta: {label}")
    return {
        "event_id": str(uuid.uuid4()),
        "action": "label",
        "validation_item_id": item_id,
        "reviewer": reviewer,
        "label": label,
        "comment": comment,
        "evidence_url_consulted": evidence_url or None,
        "guideline_version": GUIDELINE_VERSION,
        "timestamp": utc_timestamp(),
    }


def make_undo_event(item_id: str, reviewer: str, note: str) -> dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "action": "undo",
        "validation_item_id": item_id,
        "reviewer": reviewer,
        "note": note,
        "timestamp": utc_timestamp(),
    }


def export_annotations(
    output_path: Path,
    tasks: Sequence[dict[str, Any]],
    states: dict[str, dict[str, Any]],
    manifest: dict[str, dict[str, Any]] | None = None,
) -> int:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        item_id = str(task["validation_item_id"])
        event = states.get(item_id)
        if event is None:
            continue
        row = {
            "validation_item_id": item_id,
            "label": event["label"],
            "comment": str(event.get("comment") or ""),
            "evidence_url_consulted": event.get("evidence_url_consulted"),
            "reviewer": event["reviewer"],
            "guideline_version": event.get("guideline_version"),
            "decided_at": event["timestamp"],
            "event_id": event["event_id"],
        }
        if manifest is not None:
            identity = manifest[item_id]
            row = {
                **row,
                "question_id": identity["question_id"],
                "model_id": identity["model_id"],
                "category": identity["category"],
            }
        rows.append(row)
    atomic_write_jsonl(output_path, rows)
    return len(rows)


def reviewer_order(
    tasks: Sequence[dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
    seed: int,
    reviewer: str,
) -> list[dict[str, Any]]:
    with_question = [
        {**task, "question_id": manifest[str(task["validation_item_id"])]["question_id"]}
        for task in tasks
    ]
    ordered = spread_tasks(with_question, f"{seed}:reviewer:{reviewer}")
    return [
        {key: value for key, value in row.items() if key != "question_id"}
        for row in ordered
    ]


def clear_terminal() -> None:
    """Wyczyść interaktywny terminal przed pokazaniem kolejnego rekordu."""
    if not sys.stdout.isatty():
        return
    os.system("cls" if os.name == "nt" else "clear")


def print_task(
    task: dict[str, Any],
    reviewed: int,
    total: int,
    label_counts: Counter[str],
) -> None:
    width = 100
    print("=" * width)
    print(
        f"Rekord: {task['validation_item_id']} | postęp: {reviewed}/{total} "
        f"({100 * reviewed / total:.1f}%)"
    )
    print(
        "Decyzje: "
        + ", ".join(f"{label}={label_counts[label]}" for label in LABELS)
    )
    print("-" * width)
    print(f"PYTANIE:\n{task['question']}")
    print(f"\nODPOWIEDŹ MODELU:\n{task['model_response'] or '(pusta odpowiedź)'}")
    print(f"\nODPOWIEDŹ WZORCOWA:\n{task['gold_answer']}")
    print("\nDOPUSZCZALNE WARIANTY:")
    for answer in task["accepted_answers"]:
        print(f"  - {answer}")
    print(f"\nPASSAGE REFERENCYJNY:\n{task['reference_passage']}")
    print(f"\nŹRÓDŁO:\n{task['source_url']}")
    if task.get("extraction_date"):
        print(f"Data pozyskania źródła: {task['extraction_date']}")
    print("-" * width)
    print(SHORT_GUIDELINES.rstrip())
    print("=" * width)


def print_full_guidelines() -> None:
    try:
        print(GUIDELINES_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManualAnnotationError(f"Nie można odczytać instrukcji: {exc}") from exc


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "[t/N]" if not default else "[T/n]"
    while True:
        raw = input(f"{prompt} {suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in {"t", "tak", "y", "yes"}:
            return True
        if raw in {"n", "nie", "no"}:
            return False
        print("Wpisz t albo n.")


def review(args: argparse.Namespace) -> int:
    artifacts_dir = args.artifacts_dir.resolve()
    metadata = load_metadata(artifacts_dir)
    tasks, manifest = load_task_set(artifacts_dir)
    ordered = reviewer_order(tasks, manifest, int(metadata["seed"]), args.reviewer)
    all_known_ids = set(manifest)
    journal_path, output_path = annotation_paths(artifacts_dir, args.reviewer)
    events, states = load_events(journal_path, all_known_ids, args.reviewer)
    task_ids = {str(task["validation_item_id"]) for task in ordered}
    queue = deque(
        task for task in ordered if str(task["validation_item_id"]) not in states
    )
    session_history: list[str] = []

    print(f"Oceniający: {args.reviewer}")
    print(f"Dziennik: {journal_path}")
    print("Tryb zaślepiony: nazwy modeli i etykiety silver są ukryte.")

    while True:
        if not queue:
            reviewed = sum(item_id in states for item_id in task_ids)
            print(f"Ukończono ocenę: {reviewed}/{len(task_ids)}.")
            export_annotations(output_path, tasks, states)
            return 0

        task = queue[0]
        item_id = str(task["validation_item_id"])
        reviewed = sum(candidate_id in states for candidate_id in task_ids)
        counts = Counter(
            event["label"] for candidate_id, event in states.items() if candidate_id in task_ids
        )
        clear_terminal()
        print_task(task, reviewed, len(task_ids), counts)

        choice = input(
            "[c/1] correct, [h/2] hallucination, [a/3] abstention, "
            "[u] cofnij, [p] odłóż, [?] instrukcja, [q] zakończ: "
        ).strip().lower()

        if choice == "q":
            export_annotations(output_path, tasks, states)
            print("Zapisano dotychczasowy postęp.")
            return 0
        if choice == "?":
            print_full_guidelines()
            continue
        if choice == "p":
            queue.rotate(-1)
            print("Odłożono rekord na koniec bieżącej sesji.\n")
            continue
        if choice == "u":
            undo_id: str | None = None
            while session_history and undo_id is None:
                candidate = session_history.pop()
                if candidate in states and candidate in task_ids:
                    undo_id = candidate
            if undo_id is None:
                for event in reversed(events):
                    candidate = str(event["validation_item_id"])
                    if candidate in states and candidate in task_ids:
                        undo_id = candidate
                        break
            if undo_id is None:
                print("Brak aktywnej decyzji do cofnięcia.\n")
                continue
            undo_event = make_undo_event(undo_id, args.reviewer, "interactive undo")
            append_jsonl(journal_path, undo_event)
            events.append(undo_event)
            states.pop(undo_id)
            undone_task = next(row for row in ordered if row["validation_item_id"] == undo_id)
            if all(row["validation_item_id"] != undo_id for row in queue):
                queue.appendleft(undone_task)
            export_annotations(output_path, tasks, states)
            print(f"Cofnięto ocenę {undo_id}. Rekord wraca do kolejki.\n")
            continue

        label = LABEL_SHORTCUTS.get(choice)
        if label is None:
            print("Nieznana opcja.\n")
            continue

        comment = input("Komentarz (Enter = brak): ").strip()
        evidence_url = input("Dodatkowe sprawdzone źródło URL (Enter = brak): ").strip()
        print(f"Decyzja: {label}")
        if not ask_yes_no("Zapisać tę decyzję?", default=True):
            print("Decyzja nie została zapisana.\n")
            continue

        event = make_label_event(
            item_id,
            args.reviewer,
            label,
            comment,
            evidence_url,
        )
        append_jsonl(journal_path, event)
        events.append(event)
        states[item_id] = event
        session_history.append(item_id)
        queue.popleft()
        export_annotations(output_path, tasks, states)
        print(f"Zapisano {label} dla {item_id}.\n")


def undo_command(args: argparse.Namespace) -> int:
    artifacts_dir = args.artifacts_dir.resolve()
    load_metadata(artifacts_dir)
    tasks, manifest = load_task_set(artifacts_dir)
    journal_path, output_path = annotation_paths(artifacts_dir, args.reviewer)
    events, states = load_events(journal_path, set(manifest), args.reviewer)
    if not states:
        raise ManualAnnotationError("Brak aktywnych ocen do cofnięcia")

    if args.validation_item_id == "last":
        item_id = next(
            str(event["validation_item_id"])
            for event in reversed(events)
            if event["action"] == "label" and event["validation_item_id"] in states
        )
    else:
        item_id = args.validation_item_id
        if item_id not in states:
            raise ManualAnnotationError(f"Rekord {item_id} nie ma aktywnej oceny")

    event = make_undo_event(item_id, args.reviewer, args.note)
    append_jsonl(journal_path, event)
    states.pop(item_id)
    count = export_annotations(output_path, tasks, states)
    print(f"Cofnięto ocenę {item_id}. Aktywnych ocen: {count}.")
    return 0


def stats_command(args: argparse.Namespace) -> int:
    artifacts_dir = args.artifacts_dir.resolve()
    load_metadata(artifacts_dir)
    tasks, manifest = load_task_set(artifacts_dir)
    journal_path, _ = annotation_paths(artifacts_dir, args.reviewer)
    _, states = load_events(journal_path, set(manifest), args.reviewer)
    task_ids = {str(task["validation_item_id"]) for task in tasks}
    active = {item_id: state for item_id, state in states.items() if item_id in task_ids}
    labels = Counter(event["label"] for event in active.values())
    result = {
        "reviewer": args.reviewer,
        "reviewed": len(active),
        "total": len(task_ids),
        "remaining": len(task_ids) - len(active),
        "completion": len(active) / len(task_ids),
        "labels": {label: labels[label] for label in LABELS},
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Oceniający:          {args.reviewer}")
        print(f"Ocenione:            {result['reviewed']}/{result['total']} ({100 * result['completion']:.2f}%)")
        print(f"Pozostało:           {result['remaining']}")
        for label in LABELS:
            print(f"{label:20}{labels[label]}")
    return 0


def export_command(args: argparse.Namespace) -> int:
    artifacts_dir = args.artifacts_dir.resolve()
    load_metadata(artifacts_dir)
    tasks, manifest = load_task_set(artifacts_dir)
    journal_path, default_output = annotation_paths(artifacts_dir, args.reviewer)
    _, states = load_events(journal_path, set(manifest), args.reviewer)
    output = args.output.resolve() if args.output else default_output
    count = export_annotations(
        output,
        tasks,
        states,
        manifest if args.with_identities else None,
    )
    print(f"Wyeksportowano {count} ocen do {output}.")
    return 0


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
        description="Losowanie próby i interaktywna ręczna walidacja odpowiedzi.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Zalecana kolejność: prepare, a następnie niezależne review dla każdego oceniającego.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="katalog przygotowanej próby, dzienników i eksportów",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="wylosuj i zapisz próbę")
    prepare_parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    prepare_parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    prepare_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    prepare_parser.add_argument("--general", type=positive_int, default=60)
    prepare_parser.add_argument("--polish-realia", type=positive_int, default=60)
    prepare_parser.add_argument("--global", dest="global_count", type=positive_int, default=30)
    prepare_parser.add_argument(
        "--force",
        action="store_true",
        help="nadpisz wyłącznie przygotowaną próbę, jeżeli nie rozpoczęto ocen",
    )

    review_parser = subparsers.add_parser("review", help="uruchom interaktywną ocenę")
    review_parser.add_argument("--reviewer", type=validate_reviewer, required=True)

    stats_parser = subparsers.add_parser("stats", help="pokaż postęp oceniającego")
    stats_parser.add_argument("--reviewer", type=validate_reviewer, required=True)
    stats_parser.add_argument("--json", action="store_true")

    undo_parser = subparsers.add_parser("undo", help="cofnij aktywną ocenę")
    undo_parser.add_argument("validation_item_id", help="ID zadania albo 'last'")
    undo_parser.add_argument("--reviewer", type=validate_reviewer, required=True)
    undo_parser.add_argument("--note", default="manual undo")

    export_parser = subparsers.add_parser("export", help="odtwórz eksport z dziennika")
    export_parser.add_argument("--reviewer", type=validate_reviewer, required=True)
    export_parser.add_argument("--with-identities", action="store_true")
    export_parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_output_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            return prepare(args)
        if args.command == "review":
            return review(args)
        if args.command == "stats":
            return stats_command(args)
        if args.command == "undo":
            return undo_command(args)
        if args.command == "export":
            return export_command(args)
        raise ManualAnnotationError(f"Nieobsługiwana komenda: {args.command}")
    except ManualAnnotationError as exc:
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
