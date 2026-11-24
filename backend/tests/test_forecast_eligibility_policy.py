"""Structural guard for the selected FORECAST-02 daily eligibility policy."""
import json
from pathlib import Path

from django.test import SimpleTestCase


POLICY_PATH = (
    Path(__file__).resolve().parent / "forecast_cases" / "eligibility-v1.json"
)
EXPECTED_STATES = {"insufficient_history", "invalid_history", "decision_blocked"}
EXPECTED_CANDIDATES = {"daily-next-7", "weekly-next-4"}


class ForecastEligibilityPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_daily_gate_is_selected_and_model_training_remains_unimplemented(self):
        self.assertEqual(self.policy["policy_id"], "selleros-forecast-eligibility-v1")
        self.assertEqual(self.policy["revision"], 1)
        self.assertEqual(self.policy["provenance"], "synthetic-only")
        self.assertEqual(self.policy["threshold_status"], "approved_daily_v1")
        self.assertEqual(self.policy["model_training"], "NOT_IMPLEMENTED")
        self.assertEqual(
            {candidate["candidate_id"] for candidate in self.policy["candidate_gates"]},
            EXPECTED_CANDIDATES,
        )
        candidate_statuses = {
            candidate["candidate_id"]: candidate["status"]
            for candidate in self.policy["candidate_gates"]
        }
        self.assertEqual(candidate_statuses["daily-next-7"], "approved")
        self.assertEqual(candidate_statuses["weekly-next-4"], "not_selected")
        for candidate in self.policy["candidate_gates"]:
            self.assertGreater(candidate["horizon_buckets"], 0)
            self.assertGreater(candidate["minimum_complete_consecutive_buckets"], 0)
            self.assertGreater(candidate["minimum_nonzero_buckets"], 0)
            self.assertGreater(candidate["minimum_holdout_buckets"], 0)

    def test_every_insufficient_or_invalid_case_has_a_safe_disclosure(self):
        case_ids = set()
        observed_states = set()
        for case in self.policy["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            self.assertTrue(case["condition"])
            self.assertIn(case["expected_state"], EXPECTED_STATES)
            observed_states.add(case["expected_state"])
            self.assertTrue(case["required_disclosure"])
            self.assertNotIn("forecast value", case["required_disclosure"].lower())

        self.assertEqual(observed_states, EXPECTED_STATES)
