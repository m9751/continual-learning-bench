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

    def test_fixtures_tier_counts(self):
        self.assertEqual(len(self.fixtures), 35)
        tier_a = [f for f in self.fixtures if f.get("tier", "A") == "A"]
        tier_b = [f for f in self.fixtures if f.get("tier") == "B"]
        self.assertEqual(len(tier_a), 25)
        self.assertEqual(len(tier_b), 10)
        b_counts: dict[str, int] = {}
        for inst in tier_b:
            b_counts[inst["violation_category"]] = b_counts.get(inst["violation_category"], 0) + 1
        for cat in _EXPECTED_CATEGORIES:
            self.assertEqual(b_counts.get(cat, 0), 2, f"Tier B {cat} should have 2 instances")

    def test_schedule_standard(self):
        task = AOFViolationsTask(num_instances=25, schedule="standard")
        task.build_canonical_run_state()
        self.assertEqual(len(task.instances), 25)
        self.assertTrue(all(i.get("tier", "A") == "A" for i in task.instances))

    def test_schedule_tier_b(self):
        task = AOFViolationsTask(num_instances=10, schedule="tier_b")
        task.build_canonical_run_state()
        self.assertEqual(len(task.instances), 10)
        self.assertTrue(all(i.get("tier") == "B" for i in task.instances))

    def test_schedule_full(self):
        task = AOFViolationsTask(num_instances=35, schedule="full")
        task.build_canonical_run_state()
        self.assertEqual(len(task.instances), 35)

    def test_scoring_exact_match(self):
        task = AOFViolationsTask(num_instances=1, schedule="standard")
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
        task = AOFViolationsTask(num_instances=1, schedule="standard")
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

        task = AOFViolationsTask(num_instances=1, schedule="standard")
        task.build_canonical_run_state()
        query: Query = task.build_current_query()
        self.assertIn("ABOUT TO DO SOMETHING", query.prompt)

    def test_category_actions(self):
        tier_a = [f for f in self.fixtures if f.get("tier", "A") == "A"]
        by_category: dict[str, list[str]] = {}
        for inst in tier_a:
            by_category.setdefault(inst["violation_category"], []).append(inst["correct_action"])

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
