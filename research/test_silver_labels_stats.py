from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import silver_labels_stats as stats


class StatisticalHelpersTests(unittest.TestCase):
    def test_krippendorff_alpha_perfect_and_chance_level(self) -> None:
        self.assertEqual(
            stats._krippendorff_alpha_nominal(
                [["correct", "correct"], ["hallucination", "hallucination"]]
            ),
            1.0,
        )
        self.assertAlmostEqual(
            stats._krippendorff_alpha_nominal(
                [["correct", "correct"], ["correct", "hallucination"]]
            ),
            0.0,
        )

    def test_cochran_q_known_example(self) -> None:
        statistic, degrees, p_value = stats._cochran_q(
            [[1, 0, 0], [1, 1, 0], [1, 0, 1], [0, 1, 1]]
        )
        self.assertAlmostEqual(statistic, 0.5)
        self.assertEqual(degrees, 2)
        self.assertAlmostEqual(p_value, math.exp(-0.25), places=8)

    def test_stuart_maxwell_known_transition_matrix(self) -> None:
        matrix = {
            ("correct", "correct"): 1214,
            ("correct", "hallucination"): 21,
            ("correct", "abstention"): 0,
            ("hallucination", "correct"): 24,
            ("hallucination", "hallucination"): 717,
            ("hallucination", "abstention"): 0,
            ("abstention", "correct"): 0,
            ("abstention", "hallucination"): 3,
            ("abstention", "abstention"): 20,
        }
        statistic, degrees, p_value = stats._stuart_maxwell(matrix)
        self.assertAlmostEqual(statistic, 3.2)
        self.assertEqual(degrees, 2)
        self.assertAlmostEqual(p_value, math.exp(-1.6), places=8)

    def test_holm_adjustment_preserves_original_order(self) -> None:
        adjusted = stats._holm_adjust([0.03, 0.01, 0.04])
        self.assertEqual(adjusted, [0.06, 0.03, 0.06])

    def test_fisher_freeman_halton_matches_fisher_for_2x2(self) -> None:
        table = [[1, 9], [6, 4]]
        self.assertAlmostEqual(
            stats._fisher_freeman_halton_2col(table),
            stats._fisher_exact_2x2(table),
            places=12,
        )

    def test_binary_metrics_use_hallucination_as_positive_class(self) -> None:
        metrics = stats._binary_metrics(
            [
                ("hallucination", "hallucination"),
                ("hallucination", "correct"),
                ("correct", "hallucination"),
                ("abstention", "abstention"),
            ]
        )
        self.assertAlmostEqual(metrics["sensitivity"], 0.5)
        self.assertAlmostEqual(metrics["specificity"], 0.5)
        self.assertAlmostEqual(metrics["precision"], 0.5)
        self.assertAlmostEqual(metrics["f1"], 0.5)
        self.assertAlmostEqual(metrics["balanced_accuracy"], 0.5)

    def test_multiclass_metrics_report_every_class_and_macro_average(self) -> None:
        metrics = stats._multiclass_metrics(
            [
                ("correct", "correct"),
                ("hallucination", "hallucination"),
                ("abstention", "correct"),
            ]
        )
        self.assertAlmostEqual(metrics["recall_correct"], 1.0)
        self.assertAlmostEqual(metrics["precision_correct"], 0.5)
        self.assertAlmostEqual(metrics["recall_hallucination"], 1.0)
        self.assertAlmostEqual(metrics["recall_abstention"], 0.0)
        self.assertAlmostEqual(metrics["multiclass_balanced_accuracy"], 2 / 3)


class ManualAnnotationLoadingTests(unittest.TestCase):
    def test_blind_export_is_joined_with_private_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            annotations = artifacts / "annotations"
            annotations.mkdir()
            (artifacts / "private_manifest.jsonl").write_text(
                json.dumps(
                    {
                        "validation_item_id": "mv-1",
                        "model_id": "model-a",
                        "question_id": "question-1",
                        "category": "general",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (annotations / "reviewer-a.jsonl").write_text(
                json.dumps(
                    {
                        "validation_item_id": "mv-1",
                        "label": "hallucination",
                        "reviewer": "reviewer-a",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            export_path = annotations / "reviewer-a.jsonl"
            manifest_path = artifacts / "private_manifest.jsonl"
            loaded, expected = stats.discover_manual_annotations(artifacts)

            self.assertEqual(expected, 1)
            self.assertEqual(list(loaded), ["reviewer-a"])
            self.assertEqual(loaded["reviewer-a"][0].model_id, "model-a")
            self.assertEqual(loaded["reviewer-a"][0].question_id, "question-1")

            explicit, explicit_expected = stats.discover_manual_annotations(
                None,
                [export_path],
                manifest_path,
            )
            self.assertEqual(explicit_expected, 1)
            self.assertEqual(explicit, loaded)

    def test_manual_validation_section_with_three_protocols(self) -> None:
        annotations = {
            "reviewer-a": [
                stats.ManualAnnotation(
                    validation_item_id=f"mv-{model}-{question}",
                    label=label,
                    reviewer="reviewer-a",
                    model_id=model,
                    question_id=question,
                    category="general",
                )
                for model, question, label in (
                    ("model-a", "q1", "hallucination"),
                    ("model-a", "q2", "correct"),
                    ("model-b", "q1", "correct"),
                    ("model-b", "q2", "hallucination"),
                )
            ]
        }
        consensuses = {}
        protocol_labels = {
            "gold": ["hallucination", "correct", "correct", "correct"],
            "passage": ["hallucination", "correct", "correct", "hallucination"],
            "web": ["correct", "correct", "hallucination", "hallucination"],
        }
        identities = [
            ("model-a", "q1"),
            ("model-a", "q2"),
            ("model-b", "q1"),
            ("model-b", "q2"),
        ]
        for protocol, labels in protocol_labels.items():
            consensuses[protocol] = {
                key: stats.ConsensusRecord(
                    key=key,
                    label=label,
                    model_id=key[0],
                    question_id=key[1],
                    category="general",
                    available=5,
                    counts=(5, 0, 0),
                )
                for key, label in zip(identities, labels, strict=True)
            }

        lines = stats._manual_validation_section(
            annotations,
            4,
            consensuses,
            stats.AnalysisConfig(bootstrap_repetitions=10, bootstrap_seed=7),
        )
        report = "\n".join(lines)

        self.assertIn("Cohen κ", report)
        self.assertIn("Czułość", report)
        self.assertIn("Formalne porównanie trafności", report)
        self.assertIn("dokładny McNemar", report)


if __name__ == "__main__":
    unittest.main()
