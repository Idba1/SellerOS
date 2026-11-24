"""Executable examples for the documented SEGMENT-01 prototype policy."""
import json
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase


CASE_SET_PATH = Path(__file__).resolve().parent / "segment_cases" / "v1.json"


def classify_segment(case, thresholds):
    """Small test oracle for the published SEGMENT-01 precedence table."""

    purchase_count = case["recorded_purchase_count"]
    recency_days = case["recency_days"]
    trailing_spend = Decimal(case["trailing_365_day_spend_bdt"])

    if purchase_count == 0:
        return "NO_RECORDED_ELIGIBLE_PURCHASE"
    if recency_days >= thresholds["active_recency_days_maximum"] + 1:
        return "INACTIVE"
    if (
        purchase_count >= thresholds["high_value_minimum_purchase_count"]
        and trailing_spend >= Decimal(thresholds["high_value_spend_bdt"])
    ):
        return "HIGH_VALUE"
    if purchase_count >= 2:
        return "REPEAT"
    if recency_days <= thresholds["new_recency_days_maximum"]:
        return "NEW"
    return "ACTIVE_ONE_TIME"


class SegmentCaseSetTests(SimpleTestCase):
    def setUp(self):
        self.case_set = json.loads(CASE_SET_PATH.read_text(encoding="utf-8"))

    def test_case_set_has_a_safe_fixed_basis(self):
        self.assertEqual(self.case_set["case_set_id"], "selleros-segment-cases-v1")
        self.assertEqual(self.case_set["revision"], 1)
        self.assertEqual(self.case_set["provenance"], "synthetic-only")
        self.assertEqual(self.case_set["currency"], "BDT")
        self.assertEqual(self.case_set["segment_rule_version"], "segment-v1")
        self.assertEqual(
            self.case_set["eligibility"]["included_current_statuses"],
            ["DELIVERED", "RETURN_REQUESTED"],
        )
        self.assertIn(
            "RETURNED", self.case_set["eligibility"]["excluded_current_statuses"]
        )
        self.assertIn(
            "REFUNDED", self.case_set["eligibility"]["excluded_current_statuses"]
        )

    def test_every_synthetic_example_maps_to_exactly_one_explainable_segment(self):
        thresholds = self.case_set["thresholds"]
        case_ids = set()
        observed_segments = set()

        for case in self.case_set["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            self.assertTrue(case["explanation"])
            actual_segment = classify_segment(case, thresholds)
            self.assertEqual(actual_segment, case["expected_segment"])
            observed_segments.add(actual_segment)

        self.assertEqual(
            observed_segments,
            {
                "NO_RECORDED_ELIGIBLE_PURCHASE",
                "NEW",
                "ACTIVE_ONE_TIME",
                "REPEAT",
                "HIGH_VALUE",
                "INACTIVE",
            },
        )
