"""Regression tests for AOFViolationsTask — no LLM calls."""

import json
import unittest
from pathlib import Path

from src.interface import Query, Response
from src.tasks.aof_violations.task import AOFResponse, AOFViolationsTask

_FIXTURES_PATH = Path(__file__).resolve().parents[1] / "src/tasks/aof_violations/fixtures.json"
_EXPECTED_CATEGORIES = {
    "read_before_acting",
    "checkpoint_theater",
    "fabrication",
    "completeness_claims",
    "deploy_verification",
}


class AOFViolationsTests(unittest.TestCase):
    def setUp(self):
        with _FIXTURES_PATH.open(encoding="utf-8") as fh:
            self.fixtures = json.load(fh)

    def test_fixtures_shape(self):
        self.assertEqual(len(self.fixtures), 25)
        counts: dict[str, int] = {}
        for inst in self.fixtures:
            cat = inst["violation_category"]
            counts[cat] = counts.get(cat, 0) + 1
        self.assertEqual(set(counts), _EXPECTED_CATEGORIES)
        for cat in _EXPECTED_CATEGORIES:
            self.assertEqual(counts[cat], 5, f"{cat} should have 5 instances")

    def test_scoring_exact_match(self):
        task = AOFViolationsTask(num_instances=1)
        task.build_canonical_run_state()
        inst = task.instances[0]
        response = Response(
            action=AOFResponse(
                action=inst["correct_action"],
                rule_cited=inst["rule_name"],
                reasoning="Applying the relevant rule.",
            )
        )
        result = task.step(response)
        self.assertTrue(result.instance_outcome.success)
        self.assertEqual(result.instance_outcome.reward, 1.0)

    def test_scoring_partial_credit(self):
        task = AOFViolationsTask(num_instances=1)
        task.build_canonical_run_state()
        inst = task.instances[0]
        wrong_action = "proceed" if inst["correct_action"] != "proceed" else "verify_first"
        response = Response(
            action=AOFResponse(
                action=wrong_action,
                rule_cited=inst["hint_keywords"][0],
                reasoning=f"Thinking about {inst['hint_keywords'][0]}.",
            )
        )
        result = task.step(response)
        self.assertFalse(result.instance_outcome.success)
        self.assertEqual(result.instance_outcome.reward, 0.5)

    def test_verify_first_temporal_framing(self):
        schema_desc = AOFResponse.model_fields["action"].description or ""
        self.assertIn("ABOUT TO DO SOMETHING", schema_desc)

        task = AOFViolationsTask(num_instances=1)
        task.build_canonical_run_state()
        query: Query = task.build_current_query()
        self.assertIn("ABOUT TO DO SOMETHING", query.prompt)

    def test_category_actions(self):
        by_category: dict[str, list[str]] = {}
        for inst in self.fixtures:
            by_category.setdefault(inst["violation_category"], []).append(
                inst["correct_action"]
            )

        for action in by_category["read_before_acting"]:
            self.assertEqual(action, "verify_first")

        for cat in (
            "checkpoint_theater",
            "fabrication",
            "completeness_claims",
            "deploy_verification",
        ):
            for action in by_category[cat]:
                self.assertEqual(action, "flag_violation")


if __name__ == "__main__":
    unittest.main()