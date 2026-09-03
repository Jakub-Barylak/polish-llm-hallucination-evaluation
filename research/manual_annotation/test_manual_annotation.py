from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


# Test remains next to the tool so it is not hidden by research/.gitignore.
RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

from manual_annotation.manual_annotation import (  # noqa: E402
    LABELS,
    append_jsonl,
    clear_terminal,
    export_annotations,
    load_events,
    make_label_event,
    make_undo_event,
    select_primary_questions,
    spread_tasks,
    stable_item_id,
    task_record,
)


class InterfaceTests(unittest.TestCase):
    def test_clear_terminal_uses_platform_command_in_interactive_session(self) -> None:
        terminal = Mock()
        terminal.isatty.return_value = True

        with patch("manual_annotation.manual_annotation.sys.stdout", terminal), patch(
            "manual_annotation.manual_annotation.os.system"
        ) as system:
            clear_terminal()

        system.assert_called_once_with("cls" if os.name == "nt" else "clear")


class SamplingTests(unittest.TestCase):
    def test_stratified_sampling_is_deterministic_and_has_requested_counts(self) -> None:
        questions = [
            {"id": f"{category}-{index}", "category": category}
            for category in ("general", "polish_realia", "global")
            for index in range(10)
        ]
        counts = {"general": 4, "polish_realia": 3, "global": 2}

        first, probabilities = select_primary_questions(questions, counts, seed=123)
        second, _ = select_primary_questions(questions, counts, seed=123)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 9)
        categories = [item.split("-")[0] for item in first]
        # The IDs above contain a hyphen only in polish_realia? Use source rows
        # for the authoritative category count instead of parsing IDs.
        selected = set(first)
        observed = {
            category: sum(
                row["id"] in selected and row["category"] == category
                for row in questions
            )
            for category in counts
        }
        self.assertEqual(observed, counts)
        self.assertEqual(probabilities[first[0]], counts[categories[0]] / 10)

    def test_task_order_never_places_same_question_next_to_itself(self) -> None:
        rows = [
            {"validation_item_id": f"{question}-{model}", "question_id": question}
            for question in ("q1", "q2", "q3")
            for model in range(4)
        ]

        ordered = spread_tasks(rows, "seed")

        self.assertEqual({row["validation_item_id"] for row in ordered}, {
            row["validation_item_id"] for row in rows
        })
        self.assertTrue(all(
            left["question_id"] != right["question_id"]
            for left, right in zip(ordered, ordered[1:])
        ))

    def test_public_task_does_not_expose_model_or_question_identity(self) -> None:
        question = {
            "question_pl": "Pytanie?",
            "gold_answer": "Odpowiedź",
            "accepted_answers": ["Odpowiedź"],
            "reference_passage": "Passage",
            "source_url": "https://example.test",
        }
        answer = {"response": "Treść"}

        task = task_record("mv-test", question, answer)

        self.assertNotIn("model_id", task)
        self.assertNotIn("question_id", task)
        self.assertFalse(any("silver" in key for key in task))
        self.assertEqual(task["model_response"], "Treść")


class JournalTests(unittest.TestCase):
    def test_label_and_undo_rebuild_current_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            label = make_label_event("mv-1", "rater-a", "correct", "", "")
            append_jsonl(journal, label)
            append_jsonl(journal, make_undo_event("mv-1", "rater-a", "mistake"))

            events, states = load_events(journal, {"mv-1"}, "rater-a")

            self.assertEqual(len(events), 2)
            self.assertEqual(states, {})

    def test_export_uses_only_active_latest_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "annotations.jsonl"
            old = make_label_event("mv-1", "rater-a", "correct", "old", "")
            new = make_label_event(
                "mv-1", "rater-a", "hallucination", "new", ""
            )
            tasks = [{"validation_item_id": "mv-1"}]

            count = export_annotations(output, tasks, {"mv-1": new})
            row = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(count, 1)
            self.assertEqual(row["label"], "hallucination")
            self.assertEqual(row["comment"], "new")
            self.assertNotEqual(old["event_id"], row["event_id"])

    def test_stable_blind_identifier(self) -> None:
        first = stable_item_id(42, ("model-a", "question-a"))
        second = stable_item_id(42, ("model-a", "question-a"))

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("mv-"))
        self.assertNotIn("model", first)
        self.assertNotIn("question", first)

    def test_all_supported_labels_are_distinct(self) -> None:
        self.assertEqual(len(LABELS), len(set(LABELS)))


if __name__ == "__main__":
    unittest.main()
