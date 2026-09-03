#!/usr/bin/env python3
"""Uruchamia wersjonowaną ocenę odpowiedzi modeli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from verification import VerificationError
from verification.config import Experiment, load_experiments
from verification.runner import (
    annotate,
    batch_status,
    collect_batch,
    export_command,
    prepare_batch,
    preview,
    stats,
    submit_batch,
)


RESEARCH_DIR = Path(__file__).resolve().parent
REPO_DIR = RESEARCH_DIR.parent
DEFAULT_QUESTIONS = REPO_DIR / "data" / "pytania_all.jsonl"
DEFAULT_ANSWERS = RESEARCH_DIR / "odpowiedzi.jsonl"
EXPERIMENTS_PATH = RESEARCH_DIR / "verification_experiments.toml"
EXPERIMENTS = load_experiments(EXPERIMENTS_PATH)


def positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("wartość musi być liczbą całkowitą") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("wartość musi być większa od zera")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment",
        choices=sorted(EXPERIMENTS),
        required=True,
        help="jawny, wersjonowany protokół eksperymentu",
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument(
        "--model",
        help="opcjonalne nadpisanie modelu z verification_experiments.toml",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    annotate_parser = subparsers.add_parser(
        "annotate", help="uruchom lub wznów silver annotation"
    )
    annotate_parser.add_argument("--limit", type=positive_int)
    annotate_parser.add_argument("--ids", help="ID pytań rozdzielone przecinkami")
    annotate_parser.add_argument(
        "--models", nargs="+", help="annotuj tylko odpowiedzi wskazanych modeli"
    )
    annotate_parser.add_argument("--workers", type=positive_int, default=8)
    annotate_parser.add_argument(
        "--max-retries",
        type=positive_int,
        default=20,
        help="maksymalna liczba ponowień rekordu po HTTP 429 (domyślnie: 20)",
    )
    annotate_parser.add_argument("--force", action="store_true")

    batch_parser = subparsers.add_parser(
        "prepare-batch",
        help="zapisz oczekujące żądania do wejściowego JSONL Batch API",
    )
    batch_parser.add_argument(
        "--batch-input",
        type=Path,
        help="opcjonalne nadpisanie pliku wejściowego z konfiguracji",
    )
    batch_parser.add_argument("--limit", type=positive_int)
    batch_parser.add_argument("--ids", help="ID pytań rozdzielone przecinkami")
    batch_parser.add_argument(
        "--models", nargs="+", help="przygotuj tylko odpowiedzi wskazanych modeli"
    )
    batch_parser.add_argument(
        "--force",
        action="store_true",
        help="uwzględnij także adnotacje już ukończone w archiwum",
    )

    submit_parser = subparsers.add_parser(
        "submit-batch",
        help="prześlij plik wejściowy i uruchom płatne zadanie Batch API",
    )
    submit_parser.add_argument("--batch-input", type=Path)
    submit_parser.add_argument("--batch-state", type=Path)
    submit_parser.add_argument(
        "--resubmit",
        action="store_true",
        help="utwórz nowe zadanie mimo batch_id zapisanego w stanie",
    )

    status_parser = subparsers.add_parser(
        "batch-status", help="odśwież status zadania Batch API"
    )
    status_parser.add_argument("--batch-state", type=Path)
    status_parser.add_argument("--batch-id")

    collect_parser = subparsers.add_parser(
        "collect-batch",
        help="pobierz i zaimportuj wyniki zakończonego zadania Batch API",
    )
    collect_parser.add_argument("--batch-input", type=Path)
    collect_parser.add_argument("--batch-output", type=Path)
    collect_parser.add_argument("--batch-errors", type=Path)
    collect_parser.add_argument("--batch-state", type=Path)
    collect_parser.add_argument("--batch-id")

    preview_parser = subparsers.add_parser(
        "preview", help="wyświetl pełny request bez użycia API"
    )
    preview_parser.add_argument("--ids", help="ID pytań rozdzielone przecinkami")
    preview_parser.add_argument("--models", nargs="+")
    subparsers.add_parser("export", help="odtwórz wynikowy JSONL z archiwum")
    subparsers.add_parser("stats", help="pokaż statystyki etykiet i archiwum")
    return parser


def resolve_paths(args: argparse.Namespace, experiment: Experiment) -> None:
    args.experiment = experiment
    args.model = args.model or experiment.model
    args.questions = args.questions.expanduser().resolve()
    args.answers = args.answers.expanduser().resolve()
    args.output = (args.output or experiment.output_path).expanduser().resolve()
    args.archive = (args.archive or experiment.archive_path).expanduser().resolve()
    args.prompt = (args.prompt or experiment.prompt_path).expanduser().resolve()
    if hasattr(args, "batch_input"):
        args.batch_input = (
            args.batch_input or experiment.batch_input_path
        ).expanduser().resolve()
    if hasattr(args, "batch_output"):
        args.batch_output = (
            args.batch_output or experiment.batch_output_path
        ).expanduser().resolve()
    if hasattr(args, "batch_errors"):
        args.batch_errors = (
            args.batch_errors or experiment.batch_error_path
        ).expanduser().resolve()
    if hasattr(args, "batch_state"):
        args.batch_state = (
            args.batch_state or experiment.batch_state_path
        ).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    resolve_paths(args, EXPERIMENTS[args.experiment])
    try:
        commands = {
            "annotate": annotate,
            "batch-status": batch_status,
            "collect-batch": collect_batch,
            "prepare-batch": prepare_batch,
            "preview": preview,
            "export": export_command,
            "stats": stats,
            "submit-batch": submit_batch,
        }
        return commands[args.command](args)
    except (OSError, UnicodeDecodeError, VerificationError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
