"""Structural checks for the deterministic customer-assistant safety cases."""

import json
from pathlib import Path

from django.test import SimpleTestCase


CASE_SET_PATH = Path(__file__).resolve().parent / "assistant_cases" / "v1.json"
REQUIRED_CASE_TYPES = {
    "grounded_same_store_reply",
    "unknown_fact_abstention",
    "inactive_or_unavailable_product",
    "exact_stock_count_request",
    "foreign_store_request",
    "prompt_injection_or_send_request",
    "provider_unavailable",
}


class CustomerAssistantCaseSetTests(SimpleTestCase):
    def setUp(self):
        self.case_set = json.loads(CASE_SET_PATH.read_text(encoding="utf-8"))

    def test_case_set_is_versioned_synthetic_and_provider_free(self):
        self.assertEqual(
            self.case_set["case_set_id"], "selleros-customer-assistant-cases-v1"
        )
        self.assertEqual(self.case_set["case_set_revision"], 1)
        self.assertEqual(self.case_set["provenance"], "synthetic")
        self.assertIn("No provider", self.case_set["execution_boundary"])
        self.assertNotIn("api_key", json.dumps(self.case_set).casefold())

    def test_cases_cover_grounding_abstention_and_refusal_boundaries(self):
        case_ids = set()
        case_types = set()

        for case in self.case_set["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            case_types.add(case["case_type"])

            expected = case["expected_safe_behavior"]
            self.assertEqual(expected["provider_call"], "NOT_AUTHORIZED")
            self.assertEqual(expected["external_action"], "NONE")

        self.assertEqual(case_types, REQUIRED_CASE_TYPES)

    def test_security_cases_fail_closed(self):
        cases = {case["case_id"]: case for case in self.case_set["cases"]}

        foreign = cases["ASSISTANT-CASE-005"]
        self.assertNotEqual(
            foreign["authorized_store_key"], foreign["input"]["requested_store_key"]
        )
        self.assertEqual(
            foreign["expected_safe_behavior"]["outcome_state"],
            "DENIED_NO_FOREIGN_CONTEXT",
        )

        injection = cases["ASSISTANT-CASE-006"]["expected_safe_behavior"]
        self.assertEqual(injection["outcome_state"], "BLOCKED_UNTRUSTED_INSTRUCTION")
        self.assertIn("send a message", injection["must_not_do"])
