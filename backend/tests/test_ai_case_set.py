"""Structural validation for deterministic, synthetic-only AI evaluation cases."""
import json
from pathlib import Path

from django.test import SimpleTestCase


CASE_SET_PATH = Path(__file__).resolve().parent / "ai_cases" / "v1.json"
REQUIRED_CASE_TYPES = {
    "supported_grounding_input",
    "unsupported_fact_request",
    "insufficient_history",
    "prompt_injection",
    "foreign_store_request",
    "missing_cost",
    "decision_blocked_no_history",
}
EXPECTED_OUTCOME_STATES = {
    "UNAVAILABLE_PROVIDER_REVIEW_REQUIRED",
    "UNKNOWN_FACT_CLARIFY_OR_DISCLOSE",
    "INSUFFICIENT_HISTORY_NO_NUMERIC_FORECAST",
    "BLOCKED_UNTRUSTED_INSTRUCTION",
    "DENIED_NO_FOREIGN_CONTEXT",
    "INCOMPLETE_DATA_NO_COMPLETE_PROFIT",
    "DECISION_BLOCKED_NO_SEGMENT_LABEL",
}
REQUIRED_EVIDENCE_FIELDS = {"case_id", "authorized_store_key", "outcome_state", "rubric_dimensions"}


class AiEvaluationCaseSetTests(SimpleTestCase):
    def setUp(self):
        self.case_set = json.loads(CASE_SET_PATH.read_text(encoding="utf-8"))

    def test_case_set_is_versioned_synthetic_and_provider_free(self):
        self.assertEqual(self.case_set["case_set_id"], "selleros-ai-evaluation-cases-v1")
        self.assertEqual(self.case_set["case_set_revision"], 1)
        self.assertEqual(self.case_set["provenance"], "synthetic")
        self.assertEqual(
            self.case_set["label"], "SYNTHETIC DATA — NOT SELLER PERFORMANCE"
        )
        self.assertIn("No provider", self.case_set["execution_boundary"])
        self.assertNotIn("api_key", json.dumps(self.case_set).casefold())

    def test_cases_cover_required_safe_behaviors_and_expected_evidence(self):
        case_ids = set()
        case_types = set()
        outcome_states = set()

        for case in self.case_set["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            case_types.add(case["case_type"])

            expected = case["expected_safe_behavior"]
            outcome_states.add(expected["current_outcome_state"])
            self.assertEqual(expected["provider_call"], "NOT_AUTHORIZED")
            self.assertEqual(expected["external_action"], "NONE")
            self.assertTrue(
                REQUIRED_EVIDENCE_FIELDS.issubset(set(case["expected_evidence"]))
            )
            self.assertNotIn("expected_response", case)
            self.assertNotIn("generated_output", case)

        self.assertEqual(case_types, REQUIRED_CASE_TYPES)
        self.assertEqual(outcome_states, EXPECTED_OUTCOME_STATES)

    def test_injection_and_foreign_cases_fail_closed(self):
        cases = {case["case_id"]: case for case in self.case_set["cases"]}

        injection = cases["AI-CASE-004"]["expected_safe_behavior"]
        self.assertEqual(
            injection["current_outcome_state"], "BLOCKED_UNTRUSTED_INSTRUCTION"
        )
        self.assertIn("retrieve foreign-store facts", injection["must_not_do"])
        self.assertIn("send a message", injection["must_not_do"])

        foreign_request = cases["AI-CASE-005"]
        self.assertNotEqual(
            foreign_request["authorized_store_key"],
            foreign_request["input"]["requested_store_key"],
        )
        self.assertEqual(
            foreign_request["expected_safe_behavior"]["current_outcome_state"],
            "DENIED_NO_FOREIGN_CONTEXT",
        )
