"""Structural guard for the unapproved FORECAST-02 candidate eligibility policy."""
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

    def test_candidates_remain_synthetic_unapproved_and_model_free(self):
        self.assertEqual(self.policy["policy_id"], "selleros-forecast-eligibility-v1")
        self.assertEqual(self.policy["revision"], 1)
        self.assertEqual(self.policy["provenance"], "synthetic-only")
        self.assertEqual(self.policy["threshold_status"], "decision_required")
        self.assertEqual(self.policy["model_training"], "NOT_IMPLEMENTED")
        self.assertEqual(
            {candidate["candidate_id"] for candidate in self.policy["candidate_gates"]},
            EXPECTED_CANDIDATES,
        )
        for candidate in self.policy["candidate_gates"]:
            self.assertEqual(candidate["status"], "decision_required")
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
