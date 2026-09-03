#!/usr/bin/env python3
"""Tworzy raport statystyczny z wielu przebiegów eksperymentów annotatora."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


LABELS = ("correct", "hallucination", "abstention")
LABEL_ORDER = {label: index for index, label in enumerate(LABELS)}
ARCHIVE_NAME = "surowe_adnotacje.jsonl"
RESULT_NAME = "silver_labels.jsonl"
DEFAULT_BOOTSTRAP_REPETITIONS = 10_000
DEFAULT_BOOTSTRAP_SEED = 42
DEFAULT_MANUAL_ARTIFACTS = Path(__file__).resolve().parent / "manual_annotation" / "artifacts"
Key = tuple[str, str]


class StatisticsError(Exception):
    """Błąd danych wejściowych uniemożliwiający utworzenie raportu."""


@dataclass(frozen=True)
class LabelRecord:
    key: Key
    label: str
    model_id: str
    question_id: str
    category: str
    experiment_id: str | None
    token_usage: dict[str, int] | None


@dataclass(frozen=True)
class ArchiveEvent:
    key: Key
    status: str
    batch_id: str | None
    timestamp: str
    token_usage: dict[str, int] | None
    web_calls: int


@dataclass
class RunData:
    experiment: str
    run: str
    directory: Path
    records: dict[Key, LabelRecord]
    events: list[ArchiveEvent]


@dataclass(frozen=True)
class ConsensusRecord:
    key: Key
    label: str | None
    model_id: str
    question_id: str
    category: str
    available: int
    counts: tuple[int, int, int]

    @property
    def pattern(self) -> str:
        nonzero = sorted((count for count in self.counts if count), reverse=True)
        return "-".join(map(str, nonzero)) if nonzero else "brak"


@dataclass(frozen=True)
class ManualAnnotation:
    validation_item_id: str
    label: str
    reviewer: str
    model_id: str
    question_id: str
    category: str


@dataclass(frozen=True)
class AnalysisConfig:
    bootstrap_repetitions: int = DEFAULT_BOOTSTRAP_REPETITIONS
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED
    manual_artifacts: Path | None = DEFAULT_MANUAL_ARTIFACTS
    manual_annotation_paths: tuple[Path, ...] = ()
    manual_manifest_path: Path | None = None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def normalize_token_usage(value: Any) -> dict[str, int] | None:
    """Ujednolica pola usage z Chat Completions i Responses API."""
    if not isinstance(value, dict):
        return None
    input_tokens = _nonnegative_int(
        value.get("input_tokens", value.get("prompt_tokens"))
    )
    output_tokens = _nonnegative_int(
        value.get("output_tokens", value.get("completion_tokens"))
    )
    if input_tokens is None or output_tokens is None:
        return None
    input_details = value.get(
        "input_tokens_details", value.get("prompt_tokens_details", {})
    )
    output_details = value.get(
        "output_tokens_details", value.get("completion_tokens_details", {})
    )
    cached = (
        _nonnegative_int(input_details.get("cached_tokens")) or 0
        if isinstance(input_details, dict)
        else 0
    )
    reasoning = (
        _nonnegative_int(output_details.get("reasoning_tokens")) or 0
        if isinstance(output_details, dict)
        else 0
    )
    total = _nonnegative_int(value.get("total_tokens"))
    return {
        "input": input_tokens,
        "cached_input": min(cached, input_tokens),
        "uncached_input": max(0, input_tokens - cached),
        "output": output_tokens,
        "reasoning_output": reasoning,
        "total": total if total is not None else input_tokens + output_tokens,
    }


def _read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise StatisticsError(
                        f"Niepoprawny JSON w {path}, linia {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(value, dict):
                    raise StatisticsError(
                        f"{path}, linia {line_number}: oczekiwano obiektu JSON"
                    )
                yield line_number, value
    except OSError as exc:
        raise StatisticsError(f"Nie można odczytać {path}: {exc}") from exc


def _required_text(row: dict[str, Any], field: str, path: Path, line: int) -> str:
    value = row.get(field)
    if value is None or not str(value).strip():
        raise StatisticsError(f"{path}, linia {line}: brak pola {field!r}")
    return str(value)


def _load_labels(path: Path) -> dict[Key, LabelRecord]:
    records: dict[Key, LabelRecord] = {}
    for line_number, row in _read_jsonl(path):
        question_id = _required_text(row, "id", path, line_number)
        model_id = _required_text(row, "model_id", path, line_number)
        label = _required_text(row, "label", path, line_number)
        if label not in LABEL_ORDER:
            raise StatisticsError(
                f"{path}, linia {line_number}: nieznana etykieta {label!r}"
            )
        key = (model_id, question_id)
        if key in records:
            raise StatisticsError(f"{path}: zduplikowany rekord {model_id}/{question_id}")
        annotator = row.get("annotator")
        usage = (
            normalize_token_usage(annotator.get("usage"))
            if isinstance(annotator, dict)
            else None
        )
        records[key] = LabelRecord(
            key=key,
            label=label,
            model_id=model_id,
            question_id=question_id,
            category=str(row.get("category") or "unknown"),
            experiment_id=(str(row["experiment_id"]) if row.get("experiment_id") else None),
            token_usage=usage,
        )
    if not records:
        raise StatisticsError(f"Plik nie zawiera rekordów: {path}")
    return records


def _load_archive(path: Path) -> list[ArchiveEvent]:
    if not path.exists():
        return []
    events: list[ArchiveEvent] = []
    for line_number, row in _read_jsonl(path):
        question_id = _required_text(row, "question_id", path, line_number)
        model_id = _required_text(row, "model_id", path, line_number)
        response = row.get("response")
        batch = row.get("batch")
        audit = row.get("web_search_audit")
        events.append(
            ArchiveEvent(
                key=(model_id, question_id),
                status=str(row.get("status") or "unknown"),
                batch_id=(
                    str(batch["batch_id"])
                    if isinstance(batch, dict) and batch.get("batch_id")
                    else None
                ),
                timestamp=str(row.get("timestamp") or ""),
                token_usage=(
                    normalize_token_usage(response.get("usage"))
                    if isinstance(response, dict)
                    else None
                ),
                web_calls=(
                    _nonnegative_int(audit.get("calls")) or 0
                    if isinstance(audit, dict)
                    else 0
                ),
            )
        )
    return events


def _run_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value.casefold())


def discover_runs(input_path: Path) -> list[RunData]:
    if not input_path.exists():
        raise StatisticsError(f"Nie znaleziono ścieżki wejściowej: {input_path}")
    if input_path.is_file():
        if input_path.name != RESULT_NAME:
            raise StatisticsError(
                f"Plik wejściowy musi nazywać się {RESULT_NAME}; otrzymano {input_path.name}"
            )
        result_paths = [input_path]
    else:
        result_paths = sorted(input_path.rglob(RESULT_NAME))
    if not result_paths:
        raise StatisticsError(
            f"W {input_path} nie znaleziono żadnego pliku {RESULT_NAME}"
        )

    runs: list[RunData] = []
    seen_names: set[tuple[str, str]] = set()
    for result_path in result_paths:
        records = _load_labels(result_path)
        experiments = {
            record.experiment_id for record in records.values() if record.experiment_id
        }
        if len(experiments) > 1:
            raise StatisticsError(f"{result_path}: rekordy z wielu eksperymentów")
        experiment = next(iter(experiments), result_path.parent.parent.name)
        run = result_path.parent.name
        name = (experiment, run)
        if name in seen_names:
            raise StatisticsError(f"Powtórzony przebieg {experiment}/{run}")
        seen_names.add(name)
        runs.append(
            RunData(
                experiment=experiment,
                run=run,
                directory=result_path.parent,
                records=records,
                events=_load_archive(result_path.parent / ARCHIVE_NAME),
            )
        )
    return sorted(runs, key=lambda item: (item.experiment, _run_sort_key(item.run)))


def discover_manual_annotations(
    artifacts_path: Path | None,
    annotation_paths: Sequence[Path] | None = None,
    manifest_path: Path | None = None,
) -> tuple[dict[str, list[ManualAnnotation]], int]:
    """Wczytuje bieżące eksporty ocen i łączy je z prywatnym manifestem."""
    explicit_annotations = list(annotation_paths or [])
    if manifest_path is None and artifacts_path is not None:
        manifest_path = artifacts_path / "private_manifest.jsonl"
    if manifest_path is None:
        if explicit_annotations:
            raise StatisticsError(
                "Dla --manual-annotations trzeba podać --manual-manifest "
                "albo --manual-artifacts"
            )
        return {}, 0
    if not manifest_path.exists():
        if explicit_annotations:
            raise StatisticsError(f"Nie znaleziono manifestu ręcznej oceny: {manifest_path}")
        return {}, 0

    manifest: dict[str, dict[str, str]] = {}
    for line_number, row in _read_jsonl(manifest_path):
        item_id = _required_text(row, "validation_item_id", manifest_path, line_number)
        if item_id in manifest:
            raise StatisticsError(f"{manifest_path}: zduplikowany rekord {item_id}")
        manifest[item_id] = {
            "model_id": _required_text(row, "model_id", manifest_path, line_number),
            "question_id": _required_text(row, "question_id", manifest_path, line_number),
            "category": str(row.get("category") or "unknown"),
        }

    if explicit_annotations:
        selected = sorted(explicit_annotations)
        event_files = [path for path in selected if path.name.endswith(".events.jsonl")]
        if event_files:
            raise StatisticsError(
                "--manual-annotations oczekuje bieżącego eksportu, nie dziennika "
                "*.events.jsonl: " + ", ".join(map(str, event_files))
            )
        missing = [path for path in selected if not path.exists()]
        if missing:
            raise StatisticsError(
                "Nie znaleziono pliku ręcznych ocen: "
                + ", ".join(map(str, missing))
            )
    else:
        if artifacts_path is None:
            return {}, len(manifest)
        annotations_path = artifacts_path / "annotations"
        if not annotations_path.exists():
            return {}, len(manifest)
        candidates = [
            path
            for path in sorted(annotations_path.glob("*.jsonl"))
            if not path.name.endswith(".events.jsonl")
        ]
        base_names = {
            path.name
            for path in candidates
            if not path.name.endswith(".identified.jsonl")
        }
        selected = [
            path
            for path in candidates
            if not path.name.endswith(".identified.jsonl")
            or path.name.removesuffix(".identified.jsonl") + ".jsonl"
            not in base_names
        ]
    reviewers: defaultdict[str, list[ManualAnnotation]] = defaultdict(list)
    seen_by_reviewer: defaultdict[str, set[str]] = defaultdict(set)
    for path in selected:
        for line_number, row in _read_jsonl(path):
            item_id = _required_text(row, "validation_item_id", path, line_number)
            label = _required_text(row, "label", path, line_number)
            reviewer = _required_text(row, "reviewer", path, line_number)
            if label not in LABEL_ORDER:
                raise StatisticsError(
                    f"{path}, linia {line_number}: nieznana etykieta {label!r}"
                )
            identity = manifest.get(item_id)
            if identity is None:
                raise StatisticsError(
                    f"{path}, linia {line_number}: {item_id} nie występuje w manifeście"
                )
            if item_id in seen_by_reviewer[reviewer]:
                raise StatisticsError(
                    f"Powtórzona ręczna ocena {item_id} dla oceniającego {reviewer}"
                )
            seen_by_reviewer[reviewer].add(item_id)
            reviewers[reviewer].append(
                ManualAnnotation(
                    validation_item_id=item_id,
                    label=label,
                    reviewer=reviewer,
                    model_id=identity["model_id"],
                    question_id=identity["question_id"],
                    category=identity["category"],
                )
            )
    return dict(sorted(reviewers.items())), len(manifest)


def _pct(numerator: int | float, denominator: int | float) -> str:
    return f"{100 * numerator / denominator:.2f}%" if denominator else "—"


def _number(value: int | float) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return f"{value:,}".replace(",", " ")


def _rate_cell(count: int, total: int) -> str:
    if total == 0:
        return "0 (—)"
    return f"{_number(count)} ({_pct(count, total)})"


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: Sequence[object], rows: Iterable[Sequence[object]]) -> list[str]:
    materialized = [[_escape(value) for value in row] for row in rows]
    if not materialized:
        return ["_Brak danych._"]
    return [
        "| " + " | ".join(map(_escape, headers)) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(row) + " |" for row in materialized),
    ]


def _percentile(values: Sequence[int | float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_consensus(runs: Sequence[RunData], universe: set[Key]) -> dict[Key, ConsensusRecord]:
    metadata: dict[Key, LabelRecord] = {}
    for run in runs:
        metadata.update(run.records)
    result: dict[Key, ConsensusRecord] = {}
    for key in sorted(universe):
        labels = [run.records[key].label for run in runs if key in run.records]
        counts = Counter(labels)
        winner = max(LABELS, key=lambda label: counts[label]) if labels else None
        consensus = (
            winner
            if len(labels) >= 3 and winner is not None and counts[winner] > len(labels) / 2
            else None
        )
        record = metadata.get(key)
        model_id, question_id = key
        result[key] = ConsensusRecord(
            key=key,
            label=consensus,
            model_id=model_id,
            question_id=question_id,
            category=record.category if record else "unknown",
            available=len(labels),
            counts=tuple(counts[label] for label in LABELS),
        )
    return result


def _cohen_kappa(pairs: Sequence[tuple[str, str]]) -> float:
    if not pairs:
        return math.nan
    observed = sum(left == right for left, right in pairs) / len(pairs)
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum(
        left_counts[label] * right_counts[label] for label in LABELS
    ) / (len(pairs) ** 2)
    return (observed - expected) / (1 - expected) if expected < 1 else math.nan


def _krippendorff_alpha_nominal(label_sets: Sequence[Sequence[str]]) -> float:
    """Alfa Krippendorffa dla nominalnych ocen z dopuszczalnymi brakami."""
    coincidence = {left: Counter() for left in LABELS}
    total_coincidences = 0.0
    for labels in label_sets:
        valid = [label for label in labels if label in LABEL_ORDER]
        count = len(valid)
        if count < 2:
            continue
        frequencies = Counter(valid)
        for left in LABELS:
            for right in LABELS:
                pairs = frequencies[left] * (
                    frequencies[right] - (1 if left == right else 0)
                )
                coincidence[left][right] += pairs / (count - 1)
        total_coincidences += count
    if total_coincidences <= 1:
        return math.nan
    observed_disagreement = sum(
        coincidence[left][right]
        for left in LABELS
        for right in LABELS
        if left != right
    ) / total_coincidences
    marginals = {
        label: sum(coincidence[label][other] for other in LABELS)
        for label in LABELS
    }
    expected_disagreement = (
        total_coincidences**2 - sum(value**2 for value in marginals.values())
    ) / (total_coincidences * (total_coincidences - 1))
    if expected_disagreement == 0:
        return math.nan
    return 1 - observed_disagreement / expected_disagreement


def _stable_rng(seed: int, namespace: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{namespace}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _safe_div(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator if denominator else math.nan


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return math.nan, math.nan
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z**2 / (4 * total**2)
    ) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _fmt_ci(interval: tuple[float, float], digits: int = 2) -> str:
    lower, upper = interval
    if math.isnan(lower) or math.isnan(upper):
        return "—"
    return f"{100 * lower:.{digits}f}–{100 * upper:.{digits}f}%"


def _rate_ci_cell(
    count: int,
    total: int,
    interval: tuple[float, float],
) -> str:
    if total == 0:
        return "0 (—)"
    return f"{_number(count)} ({_pct(count, total)}; 95% CI {_fmt_ci(interval)})"


def _metric_ci_cell(value: float, interval: tuple[float, float]) -> str:
    if math.isnan(value) or math.isnan(interval[0]) or math.isnan(interval[1]):
        return "—"
    return f"{value:.3f} [{interval[0]:.3f}; {interval[1]:.3f}]"


def _cluster_label_intervals(
    records: Sequence[ConsensusRecord],
    repetitions: int,
    seed: int,
    namespace: str,
) -> dict[str, tuple[float, float]]:
    clusters: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        if record.label in LABEL_ORDER:
            clusters[record.question_id][str(record.label)] += 1
    vectors = [
        tuple(counts[label] for label in LABELS)
        for _, counts in sorted(clusters.items())
    ]
    if not vectors:
        return {label: (math.nan, math.nan) for label in LABELS}
    rng = _stable_rng(seed, namespace)
    samples: dict[str, list[float]] = {label: [] for label in LABELS}
    cluster_count = len(vectors)
    for _ in range(repetitions):
        totals = [0, 0, 0]
        for _ in range(cluster_count):
            vector = vectors[rng.randrange(cluster_count)]
            for index in range(len(LABELS)):
                totals[index] += vector[index]
        denominator = sum(totals)
        if denominator:
            for index, label in enumerate(LABELS):
                samples[label].append(totals[index] / denominator)
    return {
        label: (_percentile(values, 0.025), _percentile(values, 0.975))
        for label, values in samples.items()
    }


def _paired_cluster_difference_interval(
    values: Sequence[tuple[str, float]],
    repetitions: int,
    seed: int,
    namespace: str,
) -> tuple[float, float]:
    clusters: defaultdict[str, list[float]] = defaultdict(list)
    for question_id, value in values:
        clusters[question_id].append(value)
    vectors = [
        (sum(cluster_values), len(cluster_values))
        for _, cluster_values in sorted(clusters.items())
    ]
    if not vectors:
        return math.nan, math.nan
    rng = _stable_rng(seed, namespace)
    estimates: list[float] = []
    cluster_count = len(vectors)
    for _ in range(repetitions):
        numerator = 0.0
        denominator = 0
        for _ in range(cluster_count):
            cluster_sum, cluster_n = vectors[rng.randrange(cluster_count)]
            numerator += cluster_sum
            denominator += cluster_n
        estimates.append(numerator / denominator)
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def _holm_adjust(p_values: Sequence[float]) -> list[float]:
    adjusted = [math.nan] * len(p_values)
    finite = sorted(
        ((value, index) for index, value in enumerate(p_values) if not math.isnan(value)),
        key=lambda item: item[0],
    )
    running = 0.0
    count = len(finite)
    for rank, (value, original_index) in enumerate(finite):
        running = max(running, (count - rank) * value)
        adjusted[original_index] = min(1.0, running)
    return adjusted


def _cochran_q(rows: Sequence[Sequence[int]]) -> tuple[float, int, float]:
    if not rows:
        return math.nan, 0, math.nan
    treatments = len(rows[0])
    if treatments < 2 or any(len(row) != treatments for row in rows):
        return math.nan, 0, math.nan
    columns = [sum(row[index] for row in rows) for index in range(treatments)]
    row_totals = [sum(row) for row in rows]
    grand_total = sum(columns)
    denominator = treatments * grand_total - sum(value**2 for value in row_totals)
    if denominator == 0:
        return 0.0, treatments - 1, 1.0
    statistic = (treatments - 1) * (
        treatments * sum(value**2 for value in columns) - grand_total**2
    ) / denominator
    degrees = treatments - 1
    return statistic, degrees, _gamma_q(degrees / 2, statistic / 2)


def _stuart_maxwell(
    matrix: dict[tuple[str, str], int],
) -> tuple[float, int, float]:
    row = {label: sum(matrix[(label, other)] for other in LABELS) for label in LABELS}
    column = {label: sum(matrix[(other, label)] for other in LABELS) for label in LABELS}
    first, second = LABELS[:2]
    differences = [row[first] - column[first], row[second] - column[second]]
    v11 = row[first] + column[first] - 2 * matrix[(first, first)]
    v22 = row[second] + column[second] - 2 * matrix[(second, second)]
    v12 = -(matrix[(first, second)] + matrix[(second, first)])
    determinant = v11 * v22 - v12**2
    if determinant > 1e-12:
        statistic = (
            v22 * differences[0] ** 2
            - 2 * v12 * differences[0] * differences[1]
            + v11 * differences[1] ** 2
        ) / determinant
        degrees = 2
    else:
        candidates = [
            differences[index] ** 2 / value
            for index, value in enumerate((v11, v22))
            if value > 0
        ]
        if not candidates:
            return 0.0, 0, math.nan
        statistic = max(candidates)
        degrees = 1
    return statistic, degrees, _gamma_q(degrees / 2, statistic / 2)


def _chi_square_independence(
    rows: Sequence[Sequence[int]],
) -> tuple[float, int, float, float, float]:
    """Zwraca χ², df, p, V Craméra i najmniejszą oczekiwaną liczebność."""
    if len(rows) < 2 or not rows or len(rows[0]) < 2:
        return math.nan, 0, math.nan, math.nan, math.nan
    columns_count = len(rows[0])
    if any(len(row) != columns_count for row in rows):
        return math.nan, 0, math.nan, math.nan, math.nan
    row_totals = [sum(row) for row in rows]
    column_totals = [sum(row[index] for row in rows) for index in range(columns_count)]
    total = sum(row_totals)
    if total == 0 or any(value == 0 for value in row_totals + column_totals):
        return math.nan, 0, math.nan, math.nan, math.nan
    statistic = 0.0
    expected_values = []
    for row_index, observed_row in enumerate(rows):
        for column_index, observed in enumerate(observed_row):
            expected = row_totals[row_index] * column_totals[column_index] / total
            expected_values.append(expected)
            if expected:
                statistic += (observed - expected) ** 2 / expected
    degrees = (len(rows) - 1) * (columns_count - 1)
    p_value = _gamma_q(degrees / 2, statistic / 2) if degrees else math.nan
    denominator = total * min(len(rows) - 1, columns_count - 1)
    cramer = math.sqrt(statistic / denominator) if denominator else math.nan
    return statistic, degrees, p_value, cramer, min(expected_values)


def _fisher_exact_2x2(rows: Sequence[Sequence[int]]) -> float:
    if len(rows) != 2 or any(len(row) != 2 for row in rows):
        return math.nan
    a, b = rows[0]
    c, d = rows[1]
    first_total = a + b
    second_total = c + d
    first_column = a + c
    total = first_total + second_total
    if total == 0:
        return math.nan

    def probability(value: int) -> float:
        return (
            math.comb(first_total, value)
            * math.comb(second_total, first_column - value)
            / math.comb(total, first_column)
        )

    lower = max(0, first_column - second_total)
    upper = min(first_total, first_column)
    observed = probability(a)
    return min(
        1.0,
        sum(
            probability(value)
            for value in range(lower, upper + 1)
            if probability(value) <= observed + 1e-15
        ),
    )


def _fisher_freeman_halton_2col(rows: Sequence[Sequence[int]]) -> float:
    """Dwustronny test dokładny dla tabeli r×2 przy ustalonych marginesach."""
    if len(rows) < 2 or any(len(row) != 2 for row in rows):
        return math.nan
    row_totals = [sum(row) for row in rows]
    successes = sum(row[0] for row in rows)
    total = sum(row_totals)
    if total == 0:
        return math.nan
    denominator = math.comb(total, successes)

    def probability(allocation: Sequence[int]) -> float:
        numerator = math.prod(
            math.comb(row_total, value)
            for row_total, value in zip(row_totals, allocation, strict=True)
        )
        return numerator / denominator

    observed = probability([row[0] for row in rows])
    p_value = 0.0

    def enumerate_allocations(index: int, remaining: int, allocation: list[int]) -> None:
        nonlocal p_value
        if index == len(row_totals) - 1:
            if 0 <= remaining <= row_totals[index]:
                candidate = [*allocation, remaining]
                candidate_probability = probability(candidate)
                if candidate_probability <= observed + 1e-15:
                    p_value += candidate_probability
            return
        remaining_capacity = sum(row_totals[index + 1 :])
        lower = max(0, remaining - remaining_capacity)
        upper = min(row_totals[index], remaining)
        for value in range(lower, upper + 1):
            enumerate_allocations(index + 1, remaining - value, [*allocation, value])

    enumerate_allocations(0, successes, [])
    return min(1.0, p_value)


def _gamma_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x), used for chi-square p-values."""
    if x < 0 or a <= 0:
        return math.nan
    if x == 0:
        return 1.0
    epsilon = 3e-14
    tiny = 1e-300
    if x < a + 1:
        term = 1 / a
        series = term
        ap = a
        for _ in range(1000):
            ap += 1
            term *= x / ap
            series += term
            if abs(term) < abs(series) * epsilon:
                break
        p = series * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return max(0.0, min(1.0, 1 - p))
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / max(abs(b), tiny)
    if b < 0:
        d = -d
    h = d
    for index in range(1, 1001):
        an = -index * (index - a)
        b += 2
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < epsilon:
            break
    return max(0.0, min(1.0, math.exp(-x + a * math.log(x) - math.lgamma(a)) * h))


def _bowker(matrix: dict[tuple[str, str], int]) -> tuple[float, int, float]:
    statistic = 0.0
    degrees = 0
    for index, left in enumerate(LABELS):
        for right in LABELS[index + 1 :]:
            forward = matrix.get((left, right), 0)
            backward = matrix.get((right, left), 0)
            if forward + backward:
                statistic += (forward - backward) ** 2 / (forward + backward)
                degrees += 1
    p_value = _gamma_q(degrees / 2, statistic / 2) if degrees else math.nan
    return statistic, degrees, p_value


def _mcnemar_exact(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(left_only, right_only) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def _binary_metrics(pairs: Sequence[tuple[str, str]]) -> dict[str, float]:
    tp = sum(human == "hallucination" and judge == "hallucination" for human, judge in pairs)
    fn = sum(human == "hallucination" and judge != "hallucination" for human, judge in pairs)
    fp = sum(human != "hallucination" and judge == "hallucination" for human, judge in pairs)
    tn = sum(human != "hallucination" and judge != "hallucination" for human, judge in pairs)
    sensitivity = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    precision = _safe_div(tp, tp + fp)
    f1 = _safe_div(2 * tp, 2 * tp + fp + fn)
    balanced = (
        (sensitivity + specificity) / 2
        if not math.isnan(sensitivity) and not math.isnan(specificity)
        else math.nan
    )
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
        "balanced_accuracy": balanced,
        "fpr": _safe_div(fp, fp + tn),
        "fnr": _safe_div(fn, fn + tp),
    }


def _multiclass_metrics(pairs: Sequence[tuple[str, str]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    f1_values = []
    recall_values = []
    for label in LABELS:
        true_positive = sum(human == label and judge == label for human, judge in pairs)
        false_positive = sum(human != label and judge == label for human, judge in pairs)
        false_negative = sum(human == label and judge != label for human, judge in pairs)
        precision = _safe_div(true_positive, true_positive + false_positive)
        recall = _safe_div(true_positive, true_positive + false_negative)
        f1 = _safe_div(2 * true_positive, 2 * true_positive + false_positive + false_negative)
        metrics[f"precision_{label}"] = precision
        metrics[f"recall_{label}"] = recall
        metrics[f"f1_{label}"] = f1
        f1_values.append(f1)
        recall_values.append(recall)
    metrics["macro_f1"] = (
        statistics.mean(f1_values)
        if all(not math.isnan(value) for value in f1_values)
        else math.nan
    )
    metrics["multiclass_balanced_accuracy"] = (
        statistics.mean(recall_values)
        if all(not math.isnan(value) for value in recall_values)
        else math.nan
    )
    return metrics


def _manual_metrics(rows: Sequence[tuple[str, str, str]]) -> dict[str, float]:
    pairs = [(human, judge) for _, human, judge in rows]
    metrics = {
        "agreement": _safe_div(sum(human == judge for human, judge in pairs), len(pairs)),
        "kappa": _cohen_kappa(pairs),
    }
    metrics.update(_multiclass_metrics(pairs))
    metrics.update(_binary_metrics(pairs))
    return metrics


def _cluster_metric_intervals(
    rows: Sequence[tuple[str, str, str]],
    repetitions: int,
    seed: int,
    namespace: str,
) -> dict[str, tuple[float, float]]:
    clusters: defaultdict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in rows:
        clusters[row[0]].append(row)
    vectors = [values for _, values in sorted(clusters.items())]
    if not vectors:
        return {}
    rng = _stable_rng(seed, namespace)
    distributions: defaultdict[str, list[float]] = defaultdict(list)
    count = len(vectors)
    for _ in range(repetitions):
        sample: list[tuple[str, str, str]] = []
        for _ in range(count):
            sample.extend(vectors[rng.randrange(count)])
        for name, value in _manual_metrics(sample).items():
            if not math.isnan(value):
                distributions[name].append(value)
    return {
        name: (_percentile(values, 0.025), _percentile(values, 0.975))
        for name, values in distributions.items()
    }


def _manual_metric_difference_intervals(
    rows: Sequence[tuple[str, str, str, str]],
    metrics: Sequence[str],
    repetitions: int,
    seed: int,
    namespace: str,
) -> dict[str, tuple[float, tuple[float, float]]]:
    """Różnice metryk judge B - judge A ze wspólnego bootstrapu klastrowego."""
    clusters: defaultdict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for row in rows:
        clusters[row[0]].append(row)

    def differences(
        sample: Sequence[tuple[str, str, str, str]],
    ) -> dict[str, float]:
        left = [(human, judge_a) for _, human, judge_a, _ in sample]
        right = [(human, judge_b) for _, human, _, judge_b in sample]
        left_metrics = _binary_metrics(left)
        right_metrics = _binary_metrics(right)
        return {
            metric: right_metrics[metric] - left_metrics[metric]
            for metric in metrics
        }

    points = differences(rows)
    vectors = [values for _, values in sorted(clusters.items())]
    if not vectors:
        return {
            metric: (points[metric], (math.nan, math.nan)) for metric in metrics
        }
    rng = _stable_rng(seed, namespace)
    estimates: defaultdict[str, list[float]] = defaultdict(list)
    count = len(vectors)
    for _ in range(repetitions):
        sample: list[tuple[str, str, str, str]] = []
        for _ in range(count):
            sample.extend(vectors[rng.randrange(count)])
        for metric, estimate in differences(sample).items():
            if not math.isnan(estimate):
                estimates[metric].append(estimate)
    return {
        metric: (
            points[metric],
            (
                _percentile(estimates[metric], 0.025),
                _percentile(estimates[metric], 0.975),
            ),
        )
        for metric in metrics
    }


def _fmt_float(value: float, digits: int = 3) -> str:
    return "—" if math.isnan(value) else f"{value:.{digits}f}"


def _experiment_groups(runs: Sequence[RunData]) -> dict[str, list[RunData]]:
    grouped: defaultdict[str, list[RunData]] = defaultdict(list)
    for run in runs:
        grouped[run.experiment].append(run)
    return {
        experiment: sorted(values, key=lambda item: _run_sort_key(item.run))
        for experiment, values in sorted(grouped.items())
    }


def _all_keys(runs: Sequence[RunData]) -> set[Key]:
    keys = {key for run in runs for key in run.records}
    keys.update(event.key for run in runs for event in run.events)
    return keys


def _label_distribution(records: Iterable[LabelRecord | ConsensusRecord]) -> Counter[str]:
    return Counter(record.label for record in records if record.label in LABEL_ORDER)


def _status_counts(run: RunData) -> Counter[str]:
    return Counter(event.status for event in run.events)


def _completeness_section(
    groups: dict[str, list[RunData]], universe: set[Key]
) -> list[str]:
    lines = ["## 1. Kompletność danych", ""]
    rows = []
    for experiment, runs in groups.items():
        for run in runs:
            statuses = _status_counts(run)
            attempted = {event.key for event in run.events}
            retries = max(0, len(run.events) - len(attempted))
            rows.append(
                [
                    experiment,
                    run.run,
                    _number(len(universe)),
                    _number(len(run.records)),
                    _number(len(universe - set(run.records))),
                    _pct(len(run.records), len(universe)),
                    _number(len(run.events)),
                    _number(retries),
                    _number(statuses["invalid_annotation"]),
                    _number(statuses["invalid_source"]),
                ]
            )
    lines.extend(
        _table(
            [
                "Eksperyment", "Run", "Oczekiwane", "Poprawne", "Braki",
                "Kompletność", "Próby API", "Ponowienia", "invalid_annotation",
                "invalid_source",
            ],
            rows,
        )
    )

    web_runs = [run for name, values in groups.items() if "web" in name.lower() for run in values]
    if web_runs and any(event.batch_id for run in web_runs for event in run.events):
        recovery_rows = []
        for run in web_runs:
            batches: defaultdict[str, list[ArchiveEvent]] = defaultdict(list)
            for event in run.events:
                if event.batch_id:
                    batches[event.batch_id].append(event)
            recovered: set[Key] = set()
            ordered = sorted(
                batches.items(), key=lambda item: min(event.timestamp for event in item[1])
            )
            for attempt, (batch_id, events) in enumerate(ordered, start=1):
                newly_ok = {event.key for event in events if event.status == "ok"} - recovered
                recovered.update(event.key for event in events if event.status == "ok")
                statuses = Counter(event.status for event in events)
                recovery_rows.append(
                    [
                        run.experiment,
                        run.run,
                        attempt,
                        batch_id,
                        len(events),
                        len(newly_ok),
                        statuses["invalid_annotation"],
                        statuses["invalid_source"],
                        max(0, len(universe) - len(recovered)),
                    ]
                )
        lines.extend(["", "Odzyskiwanie rekordów w kolejnych batchach web:", ""])
        lines.extend(
            _table(
                [
                    "Eksperyment", "Run", "Próba", "Batch ID", "Wyniki",
                    "Nowe ok", "invalid_annotation", "invalid_source", "Pozostało",
                ],
                recovery_rows,
            )
        )
    return lines


def _distribution_section(
    groups: dict[str, list[RunData]],
    consensuses: dict[str, dict[Key, ConsensusRecord]],
    config: AnalysisConfig,
) -> list[str]:
    lines = ["## 2. Rozkład etykiet", ""]
    consensus_rows = []
    for experiment, records in consensuses.items():
        valid = [record for record in records.values() if record.label]
        counts = _label_distribution(valid)
        intervals = _cluster_label_intervals(
            valid,
            config.bootstrap_repetitions,
            config.bootstrap_seed,
            f"distribution:{experiment}:overall",
        )
        consensus_rows.append(
            [
                experiment,
                len(valid),
                *(
                    _rate_ci_cell(counts[label], len(valid), intervals[label])
                    for label in LABELS
                ),
            ]
        )
    lines.extend(
        _table(
            [
                "Eksperyment", "N z konsensusem", "correct",
                "hallucination", "abstention",
            ],
            consensus_rows,
        )
    )
    lines.extend(["", "Rozkład w poszczególnych runach:", ""])
    run_rows = []
    for experiment, runs in groups.items():
        for run in runs:
            counts = _label_distribution(run.records.values())
            run_rows.append(
                [
                    experiment,
                    run.run,
                    len(run.records),
                    *(_rate_cell(counts[label], len(run.records)) for label in LABELS),
                ]
            )
    lines.extend(
        _table(
            ["Eksperyment", "Run", "N", "correct", "hallucination", "abstention"],
            run_rows,
        )
    )

    category_rows = []
    for experiment, records in consensuses.items():
        grouped: defaultdict[str, list[ConsensusRecord]] = defaultdict(list)
        for record in records.values():
            if record.label:
                grouped[record.category].append(record)
        for category, values in sorted(grouped.items()):
            counts = _label_distribution(values)
            intervals = _cluster_label_intervals(
                values,
                config.bootstrap_repetitions,
                config.bootstrap_seed,
                f"distribution:{experiment}:category:{category}",
            )
            category_rows.append(
                [
                    experiment,
                    category,
                    len(values),
                    *(
                        _rate_ci_cell(counts[label], len(values), intervals[label])
                        for label in LABELS
                    ),
                ]
            )
    lines.extend(["", "Rozkład według kategorii:", ""])
    lines.extend(
        _table(
            ["Eksperyment", "Kategoria", "N", "correct", "hallucination", "abstention"],
            category_rows,
        )
    )
    lines.extend([
        "",
        "Przedziały dla konsensusu wyznaczono przez bootstrap całych pytań. "
        "Rozkład runów ma charakter opisowy i nie zawiera osobnych przedziałów.",
    ])
    return lines


def _stability_section(
    groups: dict[str, list[RunData]],
    consensuses: dict[str, dict[Key, ConsensusRecord]],
    universe: set[Key],
) -> list[str]:
    lines = ["## 3. Stabilność między runami", ""]
    summary_rows = []
    for experiment, runs in groups.items():
        records = consensuses[experiment]
        label_sets = [
            [run.records[key].label for run in runs if key in run.records]
            for key in sorted(universe)
        ]
        alpha = _krippendorff_alpha_nominal(label_sets)
        pairable_count = sum(record.available >= 2 for record in records.values())
        eligible = sum(record.available >= 3 for record in records.values())
        consensus_count = sum(record.label is not None for record in records.values())
        unanimous = sum(
            record.available >= 2 and max(record.counts) == record.available
            for record in records.values()
        )
        summary_rows.append(
            [
                experiment,
                len(runs),
                eligible,
                consensus_count,
                len(universe) - consensus_count,
                _rate_cell(unanimous, pairable_count),
                _fmt_float(alpha),
            ]
        )
    lines.extend(
        _table(
            [
                "Eksperyment", "Runy", "N ≥ 3", "Konsensus", "Bez konsensusu",
                "Jednomyślne (N ≥ 2)", "Krippendorff α",
            ],
            summary_rows,
        )
    )

    pattern_rows = []
    for experiment, records in consensuses.items():
        patterns = Counter(record.pattern for record in records.values())
        for pattern, count in sorted(
            patterns.items(), key=lambda item: (-sum(map(int, item[0].split("-"))) if item[0] != "brak" else 0, item[0])
        ):
            pattern_rows.append([experiment, pattern, count, _pct(count, len(records))])
    lines.extend(["", "Siła większości (liczebności etykiet, np. `4-1`):", ""])
    lines.extend(_table(["Eksperyment", "Wzorzec", "Rekordy", "Odsetek"], pattern_rows))

    pair_rows = []
    for experiment, runs in groups.items():
        for left_index, left in enumerate(runs):
            for right in runs[left_index + 1 :]:
                common = set(left.records) & set(right.records)
                pairs = [(left.records[key].label, right.records[key].label) for key in common]
                pair_rows.append(
                    [
                        experiment,
                        left.run,
                        right.run,
                        len(common),
                        _pct(sum(a == b for a, b in pairs), len(pairs)),
                        _fmt_float(_cohen_kappa(pairs)),
                    ]
                )
    lines.extend(["", "Zgodność parami między runami:", ""])
    lines.extend(
        _table(
            ["Eksperyment", "Run A", "Run B", "Wspólne N", "Zgodność", "Cohen κ"],
            pair_rows,
        )
    )
    return lines


def _comparison_section(
    consensuses: dict[str, dict[Key, ConsensusRecord]],
    config: AnalysisConfig,
) -> list[str]:
    lines = ["## 4. Porównanie protokołów na podstawie konsensusu", ""]
    names = sorted(consensuses)
    summary_rows = []
    matrices: list[tuple[str, str, dict[tuple[str, str], int], int]] = []
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left = consensuses[left_name]
            right = consensuses[right_name]
            common = sorted(
                key for key in set(left) & set(right) if left[key].label and right[key].label
            )
            pairs = [(str(left[key].label), str(right[key].label)) for key in common]
            matrix = Counter(pairs)
            left_h = sum(a == "hallucination" for a, _ in pairs)
            right_h = sum(b == "hallucination" for _, b in pairs)
            differences = [
                int(b == "hallucination") - int(a == "hallucination") for a, b in pairs
            ]
            difference = statistics.mean(differences) if differences else math.nan
            interval = _paired_cluster_difference_interval(
                [
                    (left[key].question_id, value)
                    for key, value in zip(common, differences, strict=True)
                ],
                config.bootstrap_repetitions,
                config.bootstrap_seed,
                f"protocol-difference:{left_name}:{right_name}:hallucination",
            )
            summary_rows.append(
                [
                    f"{left_name} → {right_name}",
                    len(pairs),
                    _pct(sum(a == b for a, b in pairs), len(pairs)),
                    _fmt_float(_cohen_kappa(pairs)),
                    _pct(left_h, len(pairs)),
                    _pct(right_h, len(pairs)),
                    f"{100 * difference:+.2f} pp" if not math.isnan(difference) else "—",
                    (
                        f"[{100 * interval[0]:+.2f}; {100 * interval[1]:+.2f}] pp"
                        if not math.isnan(interval[0]) else "—"
                    ),
                ]
            )
            matrices.append((left_name, right_name, matrix, len(pairs)))
    lines.extend(
        _table(
            [
                "Para", "N", "Zgodność", "Cohen κ", "Hall. A", "Hall. B",
                "Zmiana B−A", "95% CI zmiany",
            ],
            summary_rows,
        )
    )
    lines.extend([
        "",
        "Łączne różnice obejmują cztery odpowiedzi na pytanie, dlatego ich przedziały "
        "wyznaczono przez bootstrap całych pytań. Testy poniżej wykonywane są osobno "
        "dla każdego modelu, dzięki czemu pytanie pozostaje blokiem.",
    ])
    for left_name, right_name, matrix, total in matrices:
        lines.extend(["", f"Macierz przejść `{left_name}` (wiersze) → `{right_name}` (kolumny), N={total}:", ""])
        lines.extend(
            _table(
                ["A \\ B", *LABELS],
                [
                    [left, *(matrix[(left, right)] for right in LABELS)]
                    for left in LABELS
                ],
            )
        )

    models = sorted(
        {record.model_id for records in consensuses.values() for record in records.values()}
    )
    stuart_entries: list[dict[str, object]] = []
    for model in models:
        family_indices = []
        family_p = []
        for left_index, left_name in enumerate(names):
            for right_name in names[left_index + 1 :]:
                left = consensuses[left_name]
                right = consensuses[right_name]
                common = sorted(
                    key
                    for key in set(left) & set(right)
                    if key[0] == model and left[key].label and right[key].label
                )
                matrix = Counter(
                    (str(left[key].label), str(right[key].label)) for key in common
                )
                statistic, degrees, p_value = _stuart_maxwell(matrix)
                family_indices.append(len(stuart_entries))
                family_p.append(p_value)
                stuart_entries.append(
                    {
                        "model": model,
                        "pair": f"{left_name} ↔ {right_name}",
                        "n": len(common),
                        "statistic": statistic,
                        "df": degrees,
                        "p": p_value,
                        "holm": math.nan,
                    }
                )
        for index, adjusted in zip(family_indices, _holm_adjust(family_p), strict=True):
            stuart_entries[index]["holm"] = adjusted
    lines.extend(["", "Zmiana pełnego rozkładu trzech etykiet — test Stuart–Maxwell:", ""])
    lines.extend(
        _table(
            ["Model", "Para protokołów", "N", "χ²", "df", "p", "p Holma"],
            [
                [
                    entry["model"], entry["pair"], entry["n"],
                    _fmt_float(float(entry["statistic"])), entry["df"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in stuart_entries
            ],
        )
    )

    q_entries: list[dict[str, object]] = []
    posthoc_entries: list[dict[str, object]] = []
    for outcome in ("hallucination", "correct"):
        outcome_q_indices = []
        outcome_q_p = []
        for model in models:
            question_sets = [
                {
                    key[1]
                    for key, record in consensuses[name].items()
                    if key[0] == model and record.label
                }
                for name in names
            ]
            common_questions = sorted(set.intersection(*question_sets)) if question_sets else []
            rows = [
                [
                    int(consensuses[name][(model, question_id)].label == outcome)
                    for name in names
                ]
                for question_id in common_questions
            ]
            statistic, degrees, p_value = _cochran_q(rows)
            outcome_q_indices.append(len(q_entries))
            outcome_q_p.append(p_value)
            q_entries.append(
                {
                    "outcome": outcome,
                    "model": model,
                    "n": len(rows),
                    "statistic": statistic,
                    "df": degrees,
                    "p": p_value,
                    "holm": math.nan,
                }
            )
            family: list[dict[str, object]] = []
            for left_index, left_name in enumerate(names):
                for right_index in range(left_index + 1, len(names)):
                    right_name = names[right_index]
                    pair_questions = sorted(
                        {
                            key[1]
                            for key, record in consensuses[left_name].items()
                            if key[0] == model and record.label
                        }
                        & {
                            key[1]
                            for key, record in consensuses[right_name].items()
                            if key[0] == model and record.label
                        }
                    )
                    binary_pairs = [
                        (
                            int(consensuses[left_name][(model, question_id)].label == outcome),
                            int(consensuses[right_name][(model, question_id)].label == outcome),
                        )
                        for question_id in pair_questions
                    ]
                    left_only = sum(left == 1 and right == 0 for left, right in binary_pairs)
                    right_only = sum(left == 0 and right == 1 for left, right in binary_pairs)
                    family.append(
                        {
                            "outcome": outcome,
                            "model": model,
                            "pair": f"{left_name} ↔ {right_name}",
                            "n": len(binary_pairs),
                            "left_only": left_only,
                            "right_only": right_only,
                            "p": _mcnemar_exact(left_only, right_only),
                        }
                    )
            adjusted = _holm_adjust([float(entry["p"]) for entry in family])
            for entry, holm in zip(family, adjusted, strict=True):
                entry["holm"] = holm
                posthoc_entries.append(entry)
        for index, adjusted in zip(
            outcome_q_indices, _holm_adjust(outcome_q_p), strict=True
        ):
            q_entries[index]["holm"] = adjusted

    lines.extend(["", "Porównanie binarne trzech protokołów — test Cochrana Q:", ""])
    lines.extend(
        _table(
            ["Wynik", "Model", "N pytań", "Q", "df", "p", "p Holma (modele)"],
            [
                [
                    entry["outcome"], entry["model"], entry["n"],
                    _fmt_float(float(entry["statistic"])), entry["df"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in q_entries
            ],
        )
    )
    lines.extend(["", "Porównania protokołów parami — dokładny test McNemara:", ""])
    lines.extend(
        _table(
            [
                "Wynik", "Model", "Para protokołów", "Tylko A", "Tylko B",
                "N", "p", "p Holma",
            ],
            [
                [
                    entry["outcome"], entry["model"], entry["pair"],
                    entry["left_only"], entry["right_only"],
                    entry["n"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in posthoc_entries
            ],
        )
    )
    return lines


def _bootstrap_ranking(
    records: dict[Key, ConsensusRecord],
    repetitions: int,
    seed: int,
    namespace: str,
) -> tuple[list[str], dict[str, list[float]]]:
    models = sorted({record.model_id for record in records.values()})
    by_question: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for record in records.values():
        if record.label:
            by_question[record.question_id][record.model_id] = record.label
    questions = [values for _, values in sorted(by_question.items())]
    masses = {model: [0.0] * len(models) for model in models}
    if not questions or not models:
        return models, masses
    rng = _stable_rng(seed, namespace)
    for _ in range(repetitions):
        correct = Counter()
        totals = Counter()
        for _ in range(len(questions)):
            values = questions[rng.randrange(len(questions))]
            for model, label in values.items():
                totals[model] += 1
                correct[model] += label == "correct"
        rates = {
            model: _safe_div(correct[model], totals[model]) for model in models
        }
        ordered_rates = sorted(set(rates.values()), reverse=True)
        next_position = 0
        for rate in ordered_rates:
            tied = [model for model in models if rates[model] == rate]
            positions = range(next_position, next_position + len(tied))
            share = 1 / len(tied)
            for model in tied:
                for position in positions:
                    masses[model][position] += share
            next_position += len(tied)
    for model in models:
        masses[model] = [value / repetitions for value in masses[model]]
    return models, masses


def _models_section(
    consensuses: dict[str, dict[Key, ConsensusRecord]],
    config: AnalysisConfig,
) -> list[str]:
    lines = ["## 5. Wyniki modeli", ""]
    model_rows = []
    detailed_rows = []
    rankings = []
    ranking_stability_rows = []
    for experiment, records in consensuses.items():
        by_model: defaultdict[str, list[ConsensusRecord]] = defaultdict(list)
        by_model_category: defaultdict[tuple[str, str], list[ConsensusRecord]] = defaultdict(list)
        for record in records.values():
            if record.label:
                by_model[record.model_id].append(record)
                by_model_category[(record.model_id, record.category)].append(record)
        ranking_values = []
        for model, values in sorted(by_model.items()):
            counts = _label_distribution(values)
            model_rows.append(
                [
                    experiment,
                    model,
                    len(values),
                    *(
                        _rate_ci_cell(
                            counts[label],
                            len(values),
                            _wilson_interval(counts[label], len(values)),
                        )
                        for label in LABELS
                    ),
                ]
            )
            ranking_values.append((counts["correct"] / len(values), model))
        for place, (_, model) in enumerate(sorted(ranking_values, reverse=True), start=1):
            rankings.append([experiment, place, model])
        for (model, category), values in sorted(by_model_category.items()):
            counts = _label_distribution(values)
            detailed_rows.append(
                [
                    experiment,
                    model,
                    category,
                    len(values),
                    *(
                        _rate_ci_cell(
                            counts[label],
                            len(values),
                            _wilson_interval(counts[label], len(values)),
                        )
                        for label in LABELS
                    ),
                ]
            )
        stable_models, masses = _bootstrap_ranking(
            records,
            config.bootstrap_repetitions,
            config.bootstrap_seed,
            f"ranking:{experiment}",
        )
        for model in stable_models:
            probabilities = masses[model]
            mean_rank = sum(
                (position + 1) * probability
                for position, probability in enumerate(probabilities)
            )
            ranking_stability_rows.append(
                [
                    experiment,
                    model,
                    *(f"{100 * probability:.2f}%" for probability in probabilities),
                    f"{mean_rank:.3f}",
                ]
            )
    lines.extend(
        _table(
            [
                "Eksperyment", "Model", "N", "correct",
                "hallucination", "abstention",
            ],
            model_rows,
        )
    )
    lines.extend([
        "",
        "Przedziały dla pojedynczego modelu są przedziałami Wilsona. W każdej grupie "
        "model ma najwyżej jedną odpowiedź na pytanie.",
    ])
    lines.extend(["", "Ranking według odsetka `correct`:", ""])
    lines.extend(_table(["Eksperyment", "Miejsce", "Model"], rankings))
    maximum_models = max((len(values) for values in masses.values()), default=0)
    lines.extend(["", "Stabilność rankingu w bootstrapie całych pytań:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Model",
                *(f"Miejsce {position}" for position in range(1, maximum_models + 1)),
                "Średnia pozycja",
            ],
            ranking_stability_rows,
        )
    )
    lines.extend([
        "",
        "Przy remisie masa prawdopodobieństwa jest dzielona równo między zajęte miejsca.",
    ])
    lines.extend(["", "Wyniki model × kategoria:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Model", "Kategoria", "N", "correct",
                "hallucination", "abstention",
            ],
            detailed_rows,
        )
    )

    q_entries: list[dict[str, object]] = []
    model_posthoc: list[dict[str, object]] = []
    for experiment, records in consensuses.items():
        models = sorted({record.model_id for record in records.values()})
        question_sets = [
            {
                record.question_id
                for record in records.values()
                if record.model_id == model and record.label
            }
            for model in models
        ]
        common_questions = sorted(set.intersection(*question_sets)) if question_sets else []
        for outcome in ("hallucination", "correct"):
            rows = [
                [int(records[(model, question_id)].label == outcome) for model in models]
                for question_id in common_questions
            ]
            statistic, degrees, p_value = _cochran_q(rows)
            q_entries.append(
                {
                    "experiment": experiment,
                    "outcome": outcome,
                    "n": len(rows),
                    "q": statistic,
                    "df": degrees,
                    "p": p_value,
                }
            )
            family = []
            for left_index, left_model in enumerate(models):
                for right_index in range(left_index + 1, len(models)):
                    right_model = models[right_index]
                    pair_questions = sorted(
                        {
                            record.question_id
                            for record in records.values()
                            if record.model_id == left_model and record.label
                        }
                        & {
                            record.question_id
                            for record in records.values()
                            if record.model_id == right_model and record.label
                        }
                    )
                    pairs = [
                        (
                            int(records[(left_model, question_id)].label == outcome),
                            int(records[(right_model, question_id)].label == outcome),
                        )
                        for question_id in pair_questions
                    ]
                    left_only = sum(left == 1 and right == 0 for left, right in pairs)
                    right_only = sum(left == 0 and right == 1 for left, right in pairs)
                    family.append(
                        {
                            "experiment": experiment,
                            "outcome": outcome,
                            "pair": f"{left_model} ↔ {right_model}",
                            "n": len(pairs),
                            "left_only": left_only,
                            "right_only": right_only,
                            "difference": _safe_div(right_only - left_only, len(pairs)),
                            "p": _mcnemar_exact(left_only, right_only),
                        }
                    )
            adjusted = _holm_adjust([float(entry["p"]) for entry in family])
            for entry, holm in zip(family, adjusted, strict=True):
                entry["holm"] = holm
                model_posthoc.append(entry)
    lines.extend(["", "Ogólne porównanie czterech modeli — test Cochrana Q:", ""])
    lines.extend(
        _table(
            ["Eksperyment", "Wynik", "N pytań", "Q", "df", "p"],
            [
                [
                    entry["experiment"], entry["outcome"], entry["n"],
                    _fmt_float(float(entry["q"])), entry["df"],
                    _fmt_float(float(entry["p"]), 4),
                ]
                for entry in q_entries
            ],
        )
    )
    lines.extend(["", "Porównania modeli parami — dokładny test McNemara:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Wynik", "Para modeli", "Tylko A", "Tylko B",
                "N", "Zmiana B−A", "p", "p Holma",
            ],
            [
                [
                    entry["experiment"], entry["outcome"], entry["pair"],
                    entry["left_only"], entry["right_only"],
                    entry["n"],
                    (
                        f"{100 * float(entry['difference']):+.2f} pp"
                        if not math.isnan(float(entry["difference"])) else "—"
                    ),
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in model_posthoc
            ],
        )
    )

    category_entries: list[dict[str, object]] = []
    category_posthoc: list[dict[str, object]] = []
    for experiment, records in consensuses.items():
        models = sorted({record.model_id for record in records.values()})
        for outcome in ("hallucination", "correct"):
            family_start = len(category_entries)
            family_p = []
            for model in models:
                by_category: defaultdict[str, list[ConsensusRecord]] = defaultdict(list)
                for record in records.values():
                    if record.model_id == model and record.label:
                        by_category[record.category].append(record)
                categories = sorted(by_category)
                contingency = [
                    [
                        sum(record.label == outcome for record in by_category[category]),
                        sum(record.label != outcome for record in by_category[category]),
                    ]
                    for category in categories
                ]
                statistic, degrees, p_value, cramer, minimum_expected = (
                    _chi_square_independence(contingency)
                )
                family_p.append(p_value)
                category_entries.append(
                    {
                        "experiment": experiment,
                        "outcome": outcome,
                        "model": model,
                        "n": sum(map(sum, contingency)),
                        "chi": statistic,
                        "df": degrees,
                        "p": p_value,
                        "holm": math.nan,
                        "cramer": cramer,
                        "min_expected": minimum_expected,
                    }
                )
                pair_family = []
                for left_index, left_category in enumerate(categories):
                    for right_index in range(left_index + 1, len(categories)):
                        right_category = categories[right_index]
                        pair_table = [contingency[left_index], contingency[right_index]]
                        _, _, chi_p, _, pair_minimum = _chi_square_independence(pair_table)
                        method = "Fisher" if pair_minimum < 5 else "χ²"
                        p_pair = (
                            _fisher_exact_2x2(pair_table) if method == "Fisher" else chi_p
                        )
                        left_rate = _safe_div(pair_table[0][0], sum(pair_table[0]))
                        right_rate = _safe_div(pair_table[1][0], sum(pair_table[1]))
                        pair_family.append(
                            {
                                "experiment": experiment,
                                "outcome": outcome,
                                "model": model,
                                "pair": f"{left_category} ↔ {right_category}",
                                "difference": right_rate - left_rate,
                                "method": method,
                                "p": p_pair,
                            }
                        )
                adjusted_pairs = _holm_adjust(
                    [float(entry["p"]) for entry in pair_family]
                )
                for entry, holm in zip(pair_family, adjusted_pairs, strict=True):
                    entry["holm"] = holm
                    category_posthoc.append(entry)
            adjusted_models = _holm_adjust(family_p)
            for offset, adjusted in enumerate(adjusted_models):
                category_entries[family_start + offset]["holm"] = adjusted

    lines.extend(["", "Różnice pomiędzy kategoriami — test chi-kwadrat:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Wynik", "Model", "N", "χ²", "df", "p",
                "p Holma (modele)", "V Craméra", "Min. oczekiwana",
            ],
            [
                [
                    entry["experiment"], entry["outcome"], entry["model"], entry["n"],
                    _fmt_float(float(entry["chi"])), entry["df"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                    _fmt_float(float(entry["cramer"])),
                    _fmt_float(float(entry["min_expected"]), 2),
                ]
                for entry in category_entries
            ],
        )
    )
    lines.extend(["", "Porównania kategorii parami:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Wynik", "Model", "Para kategorii", "Zmiana B−A",
                "Test", "p", "p Holma",
            ],
            [
                [
                    entry["experiment"], entry["outcome"], entry["model"], entry["pair"],
                    f"{100 * float(entry['difference']):+.2f} pp",
                    entry["method"], _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in category_posthoc
            ],
        )
    )
    return lines


def _manual_validation_section(
    annotations: dict[str, list[ManualAnnotation]],
    expected_annotations: int,
    consensuses: dict[str, dict[Key, ConsensusRecord]],
    config: AnalysisConfig,
) -> list[str]:
    lines = ["## 6. Ręczna walidacja sędziego LLM", ""]
    if not annotations:
        lines.extend(
            [
                "_Nie znaleziono eksportów ręcznej oceny. Sekcja zostanie uzupełniona "
                "automatycznie po pojawieniu się plików `annotations/*.jsonl`._",
            ]
        )
        return lines

    completion_rows = []
    for reviewer, values in annotations.items():
        counts = Counter(value.label for value in values)
        completion_rows.append(
            [
                reviewer,
                len(values),
                expected_annotations,
                _pct(len(values), expected_annotations),
                len({value.question_id for value in values}),
                *(_rate_cell(counts[label], len(values)) for label in LABELS),
            ]
        )
    lines.extend(
        _table(
            [
                "Oceniający", "Ocenione", "Plan", "Kompletność", "Pytania",
                "correct", "hallucination", "abstention",
            ],
            completion_rows,
        )
    )
    if any(len(values) < expected_annotations for values in annotations.values()):
        lines.extend(
            [
                "",
                "**Uwaga:** co najmniej jeden eksport jest niekompletny. Wyniki ręcznej "
                "walidacji mają do czasu zakończenia oceny charakter wstępny.",
            ]
        )

    agreement_rows = []
    class_metric_rows = []
    multiclass_summary_rows = []
    detection_rows = []
    confusion_tables: list[tuple[str, str, Counter[tuple[str, str]], int]] = []
    annotations_by_reviewer: dict[str, dict[Key, ManualAnnotation]] = {
        reviewer: {(value.model_id, value.question_id): value for value in values}
        for reviewer, values in annotations.items()
    }
    if len(annotations_by_reviewer) > 1:
        human_agreement_rows = []
        reviewer_names = sorted(annotations_by_reviewer)
        for left_index, left_name in enumerate(reviewer_names):
            for right_name in reviewer_names[left_index + 1 :]:
                left = annotations_by_reviewer[left_name]
                right = annotations_by_reviewer[right_name]
                common = sorted(set(left) & set(right))
                rows = [
                    (left[key].question_id, left[key].label, right[key].label)
                    for key in common
                ]
                point = _manual_metrics(rows)
                intervals = _cluster_metric_intervals(
                    rows,
                    config.bootstrap_repetitions,
                    config.bootstrap_seed,
                    f"human-agreement:{left_name}:{right_name}",
                )
                human_agreement_rows.append(
                    [
                        f"{left_name} ↔ {right_name}",
                        len(rows),
                        len({row[0] for row in rows}),
                        _metric_ci_cell(
                            point["agreement"],
                            intervals.get("agreement", (math.nan, math.nan)),
                        ),
                        _metric_ci_cell(
                            point["kappa"],
                            intervals.get("kappa", (math.nan, math.nan)),
                        ),
                    ]
                )
        lines.extend(["", "Zgodność pomiędzy oceniającymi:", ""])
        lines.extend(
            _table(
                ["Para", "Wspólne N", "Pytania", "Zgodność", "Cohen κ"],
                human_agreement_rows,
            )
        )
    for reviewer, manual_by_key in annotations_by_reviewer.items():
        for experiment, records in consensuses.items():
            common = sorted(
                key
                for key in set(manual_by_key) & set(records)
                if records[key].label
            )
            rows = [
                (
                    manual_by_key[key].question_id,
                    manual_by_key[key].label,
                    str(records[key].label),
                )
                for key in common
            ]
            point = _manual_metrics(rows)
            intervals = _cluster_metric_intervals(
                rows,
                config.bootstrap_repetitions,
                config.bootstrap_seed,
                f"manual:{reviewer}:{experiment}",
            )
            agreement_rows.append(
                [
                    reviewer,
                    experiment,
                    len(rows),
                    len({row[0] for row in rows}),
                    _metric_ci_cell(point["agreement"], intervals.get("agreement", (math.nan, math.nan))),
                    _metric_ci_cell(point["kappa"], intervals.get("kappa", (math.nan, math.nan))),
                ]
            )
            for label in LABELS:
                support = sum(human == label for _, human, _ in rows)
                class_metric_rows.append(
                    [
                        reviewer,
                        experiment,
                        label,
                        support,
                        _metric_ci_cell(
                            point[f"precision_{label}"],
                            intervals.get(f"precision_{label}", (math.nan, math.nan)),
                        ),
                        _metric_ci_cell(
                            point[f"recall_{label}"],
                            intervals.get(f"recall_{label}", (math.nan, math.nan)),
                        ),
                        _metric_ci_cell(
                            point[f"f1_{label}"],
                            intervals.get(f"f1_{label}", (math.nan, math.nan)),
                        ),
                    ]
                )
            multiclass_summary_rows.append(
                [
                    reviewer,
                    experiment,
                    len(rows),
                    _metric_ci_cell(
                        point["macro_f1"],
                        intervals.get("macro_f1", (math.nan, math.nan)),
                    ),
                    _metric_ci_cell(
                        point["multiclass_balanced_accuracy"],
                        intervals.get(
                            "multiclass_balanced_accuracy", (math.nan, math.nan)
                        ),
                    ),
                ]
            )
            detection_rows.append(
                [
                    reviewer,
                    experiment,
                    len(rows),
                    *(
                        _metric_ci_cell(point[name], intervals.get(name, (math.nan, math.nan)))
                        for name in (
                            "sensitivity", "specificity", "precision", "f1",
                            "balanced_accuracy", "fpr", "fnr",
                        )
                    ),
                ]
            )
            confusion_tables.append(
                (
                    reviewer,
                    experiment,
                    Counter((human, judge) for _, human, judge in rows),
                    len(rows),
                )
            )

    lines.extend(["", "Zgodność trójklasowa z oceną człowieka (estymata [95% CI]):", ""])
    lines.extend(
        _table(
            ["Oceniający", "Protokół", "N", "Pytania", "Zgodność", "Cohen κ"],
            agreement_rows,
        )
    )
    lines.extend(["", "Metryki trójklasowe według klasy (estymata [95% CI]):", ""])
    lines.extend(
        _table(
            [
                "Oceniający", "Protokół", "Klasa", "Support człowieka",
                "Precision", "Recall", "F1",
            ],
            class_metric_rows,
        )
    )
    lines.extend(["", "Podsumowanie trójklasowe (estymata [95% CI]):", ""])
    lines.extend(
        _table(
            ["Oceniający", "Protokół", "N", "Macro-F1", "Balanced accuracy"],
            multiclass_summary_rows,
        )
    )
    lines.extend(
        [
            "",
            "Wartości macro są nieważoną średnią wyników trzech klas. Wyniki klasy "
            "`abstention` należy interpretować ostrożnie ze względu na bardzo małe support.",
        ]
    )
    lines.extend(["", "Detekcja klasy `hallucination` (estymata [95% CI]):", ""])
    lines.extend(
        _table(
            [
                "Oceniający", "Protokół", "N", "Czułość", "Swoistość",
                "Precision", "F1", "Balanced accuracy", "FPR", "FNR",
            ],
            detection_rows,
        )
    )
    lines.extend(
        [
            "",
            "Klasa dodatnia to `hallucination`; `correct` i `abstention` tworzą klasę "
            "ujemną. Przedziały wyznaczono przez bootstrap całych pytań.",
        ]
    )
    for reviewer, experiment, matrix, total in confusion_tables:
        lines.extend(
            [
                "",
                f"Macierz pomyłek człowiek (wiersze) → `{experiment}` (kolumny), "
                f"oceniający `{reviewer}`, N={total}:",
                "",
            ]
        )
        lines.extend(
            _table(
                ["Człowiek \\ LLM", *LABELS],
                [
                    [human, *(matrix[(human, judge)] for judge in LABELS)]
                    for human in LABELS
                ],
            )
        )

    difference_rows = []
    protocol_names = sorted(consensuses)
    for reviewer, manual_by_key in annotations_by_reviewer.items():
        for left_index, left_name in enumerate(protocol_names):
            for right_name in protocol_names[left_index + 1 :]:
                common = sorted(
                    key
                    for key in manual_by_key
                    if key in consensuses[left_name]
                    and key in consensuses[right_name]
                    and consensuses[left_name][key].label
                    and consensuses[right_name][key].label
                )
                rows = [
                    (
                        manual_by_key[key].question_id,
                        manual_by_key[key].label,
                        str(consensuses[left_name][key].label),
                        str(consensuses[right_name][key].label),
                    )
                    for key in common
                ]
                compared_metrics = (
                    "sensitivity", "specificity", "precision", "f1",
                    "balanced_accuracy",
                )
                differences = _manual_metric_difference_intervals(
                    rows,
                    compared_metrics,
                    config.bootstrap_repetitions,
                    config.bootstrap_seed,
                    f"manual-difference:{reviewer}:{left_name}:{right_name}",
                )
                for metric in compared_metrics:
                    point, interval = differences[metric]
                    difference_rows.append(
                        [
                            reviewer,
                            f"{left_name} → {right_name}",
                            metric,
                            len(rows),
                            f"{100 * point:+.2f} pp" if not math.isnan(point) else "—",
                            (
                                f"[{100 * interval[0]:+.2f}; {100 * interval[1]:+.2f}] pp"
                                if not math.isnan(interval[0]) else "—"
                            ),
                        ]
                    )
    lines.extend(["", "Różnice trafności protokołów względem ręcznych etykiet (B−A):", ""])
    lines.extend(
        _table(
            ["Oceniający", "Para", "Metryka", "N", "Różnica", "95% CI"],
            difference_rows,
        )
    )

    q_entries: list[dict[str, object]] = []
    posthoc_entries: list[dict[str, object]] = []
    models = sorted(
        {annotation.model_id for values in annotations.values() for annotation in values}
    )
    for reviewer, manual_by_key in annotations_by_reviewer.items():
        for endpoint in ("accuracy", "sensitivity", "specificity"):
            endpoint_indices = []
            endpoint_p = []
            for model in models:
                common_questions = sorted(
                    question_id
                    for candidate_model, question_id in manual_by_key
                    if candidate_model == model
                    and all(
                        (model, question_id) in consensuses[name]
                        and consensuses[name][(model, question_id)].label
                        for name in protocol_names
                    )
                )
                rows = []
                for question_id in common_questions:
                    key = (model, question_id)
                    human_positive = manual_by_key[key].label == "hallucination"
                    if endpoint == "sensitivity" and not human_positive:
                        continue
                    if endpoint == "specificity" and human_positive:
                        continue
                    values = []
                    for name in protocol_names:
                        judge_positive = consensuses[name][key].label == "hallucination"
                        if endpoint == "accuracy":
                            values.append(int(judge_positive == human_positive))
                        elif endpoint == "sensitivity":
                            values.append(int(judge_positive))
                        else:
                            values.append(int(not judge_positive))
                    rows.append(values)
                statistic, degrees, p_value = _cochran_q(rows)
                endpoint_indices.append(len(q_entries))
                endpoint_p.append(p_value)
                q_entries.append(
                    {
                        "reviewer": reviewer,
                        "endpoint": endpoint,
                        "model": model,
                        "n": len(rows),
                        "q": statistic,
                        "df": degrees,
                        "p": p_value,
                        "holm": math.nan,
                    }
                )
                family = []
                for left_index, left_name in enumerate(protocol_names):
                    for right_index in range(left_index + 1, len(protocol_names)):
                        right_name = protocol_names[right_index]
                        pairs = []
                        for candidate_model, question_id in sorted(manual_by_key):
                            if candidate_model != model:
                                continue
                            key = (model, question_id)
                            if (
                                key not in consensuses[left_name]
                                or key not in consensuses[right_name]
                                or not consensuses[left_name][key].label
                                or not consensuses[right_name][key].label
                            ):
                                continue
                            human_positive = manual_by_key[key].label == "hallucination"
                            if endpoint == "sensitivity" and not human_positive:
                                continue
                            if endpoint == "specificity" and human_positive:
                                continue
                            left_positive = consensuses[left_name][key].label == "hallucination"
                            right_positive = consensuses[right_name][key].label == "hallucination"
                            if endpoint == "accuracy":
                                pairs.append(
                                    (
                                        int(left_positive == human_positive),
                                        int(right_positive == human_positive),
                                    )
                                )
                            elif endpoint == "sensitivity":
                                pairs.append((int(left_positive), int(right_positive)))
                            else:
                                pairs.append((int(not left_positive), int(not right_positive)))
                        left_only = sum(left == 1 and right == 0 for left, right in pairs)
                        right_only = sum(left == 0 and right == 1 for left, right in pairs)
                        family.append(
                            {
                                "reviewer": reviewer,
                                "endpoint": endpoint,
                                "model": model,
                                "pair": f"{left_name} ↔ {right_name}",
                                "n": len(pairs),
                                "left_only": left_only,
                                "right_only": right_only,
                                "p": _mcnemar_exact(left_only, right_only),
                            }
                        )
                adjusted = _holm_adjust([float(entry["p"]) for entry in family])
                for entry, holm in zip(family, adjusted, strict=True):
                    entry["holm"] = holm
                    posthoc_entries.append(entry)
            for index, adjusted in zip(
                endpoint_indices, _holm_adjust(endpoint_p), strict=True
            ):
                q_entries[index]["holm"] = adjusted

    lines.extend(["", "Formalne porównanie trafności trzech protokołów — Cochran Q:", ""])
    lines.extend(
        _table(
            [
                "Oceniający", "Metryka", "Model", "N pytań", "Q", "df", "p",
                "p Holma (modele)",
            ],
            [
                [
                    entry["reviewer"], entry["endpoint"], entry["model"], entry["n"],
                    _fmt_float(float(entry["q"])), entry["df"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in q_entries
            ],
        )
    )
    lines.extend(["", "Porównania trafności protokołów parami — dokładny McNemar:", ""])
    lines.extend(
        _table(
            [
                "Oceniający", "Metryka", "Model", "Para", "Tylko A", "Tylko B",
                "N", "p", "p Holma",
            ],
            [
                [
                    entry["reviewer"], entry["endpoint"], entry["model"], entry["pair"],
                    entry["left_only"], entry["right_only"],
                    entry["n"],
                    _fmt_float(float(entry["p"]), 4),
                    _fmt_float(float(entry["holm"]), 4),
                ]
                for entry in posthoc_entries
            ],
        )
    )
    return lines


def _missingness_section(
    consensuses: dict[str, dict[Key, ConsensusRecord]],
) -> list[str]:
    lines = ["## 7. Braki konsensusu", ""]
    detail_rows = []
    test_rows = []
    for experiment, records in consensuses.items():
        for dimension in ("model", "category"):
            grouped: defaultdict[str, list[ConsensusRecord]] = defaultdict(list)
            for record in records.values():
                value = record.model_id if dimension == "model" else record.category
                grouped[value].append(record)
            contingency = []
            for value, items in sorted(grouped.items()):
                missing = sum(item.label is None for item in items)
                available = len(items) - missing
                contingency.append([missing, available])
                detail_rows.append(
                    [experiment, dimension, value, len(items), missing, _pct(missing, len(items))]
                )
            statistic, degrees, p_value, cramer, minimum_expected = (
                _chi_square_independence(contingency)
            )
            method = "χ²"
            if math.isnan(minimum_expected):
                method = "—"
            elif minimum_expected < 5:
                p_value = _fisher_freeman_halton_2col(contingency)
                method = "Fisher–Freeman–Halton"
            test_rows.append(
                [
                    experiment, dimension, method, _fmt_float(statistic), degrees,
                    _fmt_float(p_value, 4), _fmt_float(cramer),
                    _fmt_float(minimum_expected, 2),
                ]
            )
    lines.extend(
        _table(
            ["Eksperyment", "Przekrój", "Grupa", "Oczekiwane", "Braki", "Odsetek"],
            detail_rows,
        )
    )
    lines.extend(["", "Zależność braków od modelu lub kategorii:", ""])
    lines.extend(
        _table(
            [
                "Eksperyment", "Zmienna", "Test", "χ²", "df", "p",
                "V Craméra", "Min. oczekiwana",
            ],
            test_rows,
        )
    )
    lines.extend(
        [
            "",
            "Gdy minimalna oczekiwana liczebność jest mniejsza niż 5, raport podaje "
            "dokładną wartość p testu Fishera–Freemana–Haltona zamiast asymptotycznej "
            "wartości p testu chi-kwadrat. Statystykę χ² i V Craméra pozostawiono jako "
            "opis wielkości zależności.",
        ]
    )
    return lines


def _tokens_section(groups: dict[str, list[RunData]]) -> list[str]:
    lines = ["## 8. Tokeny i wydajność", ""]
    rows = []
    status_rows = []
    for experiment, runs in groups.items():
        for run in runs:
            archive_usages = [event.token_usage for event in run.events if event.token_usage]
            if archive_usages:
                usages = archive_usages
                source = "archiwum (wszystkie próby)"
            else:
                usages = [record.token_usage for record in run.records.values() if record.token_usage]
                source = "eksport (tylko poprawne)"
            total_values = [usage["total"] for usage in usages]
            rows.append(
                [
                    experiment,
                    run.run,
                    source,
                    len(usages),
                    sum(usage["input"] for usage in usages),
                    sum(usage["cached_input"] for usage in usages),
                    sum(usage["uncached_input"] for usage in usages),
                    sum(usage["output"] for usage in usages),
                    sum(usage["reasoning_output"] for usage in usages),
                    sum(total_values),
                    f"{statistics.mean(total_values):.1f}" if total_values else "—",
                    f"{statistics.median(total_values):.1f}" if total_values else "—",
                    f"{_percentile(total_values, 0.95):.1f}" if total_values else "—",
                    sum(event.web_calls for event in run.events),
                    f"{len(run.events) / len(run.records):.3f}" if run.records and run.events else "—",
                ]
            )
            statuses: defaultdict[str, list[dict[str, int]]] = defaultdict(list)
            for event in run.events:
                if event.token_usage:
                    statuses[event.status].append(event.token_usage)
            for status, values in sorted(statuses.items()):
                status_rows.append(
                    [
                        experiment,
                        run.run,
                        status,
                        len(values),
                        sum(value["input"] for value in values),
                        sum(value["output"] for value in values),
                        sum(value["total"] for value in values),
                    ]
                )
    lines.extend(
        _table(
            [
                "Eksperyment", "Run", "Źródło usage", "Wywołania", "Input", "Cache",
                "Bez cache", "Output", "Reasoning", "Total", "Śr. total",
                "Mediana", "P95", "Web calls", "Próby / wynik",
            ],
            rows,
        )
    )
    if status_rows:
        lines.extend(["", "Tokeny według statusu odpowiedzi API:", ""])
        lines.extend(
            _table(
                ["Eksperyment", "Run", "Status", "Wywołania", "Input", "Output", "Total"],
                status_rows,
            )
        )
    return lines


def build_report(
    runs: Sequence[RunData],
    input_path: Path,
    config: AnalysisConfig | None = None,
    manual_annotations: dict[str, list[ManualAnnotation]] | None = None,
    expected_manual_annotations: int = 0,
) -> str:
    config = config or AnalysisConfig()
    manual_annotations = manual_annotations or {}
    groups = _experiment_groups(runs)
    universe = _all_keys(runs)
    if not universe:
        raise StatisticsError("Nie znaleziono żadnych par model–pytanie")
    consensuses = {
        experiment: build_consensus(experiment_runs, universe)
        for experiment, experiment_runs in groups.items()
    }
    models = {key[0] for key in universe}
    questions = {key[1] for key in universe}
    lines = [
        "# Statystyki eksperymentów annotatora",
        "",
        f"- Ścieżka wejściowa: `{input_path}`",
        f"- Eksperymenty: {len(groups)} ({', '.join(f'`{name}`' for name in groups)})",
        f"- Przebiegi: {len(runs)}",
        f"- Oczekiwane pary model–pytanie: {_number(len(universe))}",
        f"- Modele generujące: {len(models)}",
        f"- Pytania: {_number(len(questions))}",
        f"- Bootstrap: {_number(config.bootstrap_repetitions)} powtórzeń, seed `{config.bootstrap_seed}`",
    ]
    manual_count = sum(len(values) for values in manual_annotations.values())
    if manual_count:
        lines.append(
            f"- Ręczna walidacja: {_number(manual_count)} ocen, "
            f"oceniający: {', '.join(f'`{name}`' for name in manual_annotations)}"
        )
        if config.manual_annotation_paths:
            sources = ", ".join(f"`{path}`" for path in config.manual_annotation_paths)
            lines.append(f"- Pliki ręcznych ocen: {sources}")
        elif config.manual_artifacts is not None:
            lines.append(
                f"- Katalog ręcznych ocen: `{config.manual_artifacts / 'annotations'}`"
            )
        if config.manual_manifest_path is not None:
            lines.append(f"- Manifest ręcznej oceny: `{config.manual_manifest_path}`")
    lines.append("")
    lines.extend(_completeness_section(groups, universe))
    lines.extend([""])
    lines.extend(_distribution_section(groups, consensuses, config))
    lines.extend([""])
    lines.extend(_stability_section(groups, consensuses, universe))
    lines.extend([""])
    lines.extend(_comparison_section(consensuses, config))
    lines.extend([""])
    lines.extend(_models_section(consensuses, config))
    lines.extend([""])
    lines.extend(
        _manual_validation_section(
            manual_annotations,
            expected_manual_annotations,
            consensuses,
            config,
        )
    )
    lines.extend([""])
    lines.extend(_missingness_section(consensuses))
    lines.extend([""])
    lines.extend(_tokens_section(groups))
    return "\n".join(lines).rstrip() + "\n"


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(content)
            temporary_name = handle.name
        Path(temporary_name).replace(path)
    except OSError as exc:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        raise StatisticsError(f"Nie można zapisać raportu {path}: {exc}") from exc


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("wartość musi być liczbą całkowitą") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("wartość musi być większa od zera")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help=f"katalog z eksperymentami/runami albo pojedynczy plik {RESULT_NAME}",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="opcjonalny plik docelowy Markdown; bez niego raport trafia na stdout",
    )
    parser.add_argument(
        "--manual-artifacts",
        type=Path,
        default=DEFAULT_MANUAL_ARTIFACTS,
        help=(
            "katalog artifacts ręcznej walidacji; eksporty annotations/*.jsonl "
            "są dołączane automatycznie"
        ),
    )
    parser.add_argument(
        "--manual-annotations",
        type=Path,
        nargs="+",
        help=(
            "jawne pliki JSONL z bieżącymi eksportami ręcznych ocen; "
            "pomija automatyczne wyszukiwanie w katalogu annotations"
        ),
    )
    parser.add_argument(
        "--manual-manifest",
        type=Path,
        help=(
            "prywatny manifest JSONL mapujący validation_item_id na model i pytanie; "
            "domyślnie <manual-artifacts>/private_manifest.jsonl"
        ),
    )
    parser.add_argument(
        "--bootstrap-repetitions",
        type=_positive_int,
        default=DEFAULT_BOOTSTRAP_REPETITIONS,
        help=f"liczba powtórzeń bootstrapu (domyślnie {DEFAULT_BOOTSTRAP_REPETITIONS})",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=DEFAULT_BOOTSTRAP_SEED,
        help=f"ziarno bootstrapu (domyślnie {DEFAULT_BOOTSTRAP_SEED})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    try:
        runs = discover_runs(input_path)
        manual_path = args.manual_artifacts.expanduser().resolve()
        manual_files = (
            [path.expanduser().resolve() for path in args.manual_annotations]
            if args.manual_annotations
            else None
        )
        manual_manifest = (
            args.manual_manifest.expanduser().resolve()
            if args.manual_manifest
            else None
        )
        resolved_manual_manifest = manual_manifest or (
            manual_path / "private_manifest.jsonl"
        )
        manual_annotations, expected_manual = discover_manual_annotations(
            manual_path,
            manual_files,
            manual_manifest,
        )
        config = AnalysisConfig(
            bootstrap_repetitions=args.bootstrap_repetitions,
            bootstrap_seed=args.bootstrap_seed,
            manual_artifacts=manual_path,
            manual_annotation_paths=tuple(manual_files or ()),
            manual_manifest_path=resolved_manual_manifest,
        )
        report = build_report(
            runs,
            input_path,
            config,
            manual_annotations,
            expected_manual,
        )
        if args.output is None:
            sys.stdout.write(report)
        else:
            output_path = args.output.expanduser().resolve()
            source_paths = {run.directory / RESULT_NAME for run in runs}
            if output_path in source_paths:
                raise StatisticsError(
                    "Plik docelowy nie może nadpisywać wejściowego "
                    f"{RESULT_NAME}: {output_path}"
                )
            _write_atomic(output_path, report)
            print(f"Zapisano raport: {output_path}")
    except (OSError, StatisticsError, UnicodeDecodeError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
