"""Structural validation for the versioned ADVISOR-01 evidence cases."""
import json
from pathlib import Path

from django.test import SimpleTestCase


CASE_SET_PATH = Path(__file__).resolve().parent / "advisor_cases" / "v1.json"
SUPPORTED_INSIGHTS = {
    "base_delivered_sales_snapshot": "/api/v1/analytics/sales-summary/",
    "product_delivery_snapshot": "/api/v1/analytics/product-performance/",
    "estimated_profit_completeness_snapshot": "/api/v1/profit/summary/",
    "low_stock_threshold_snapshot": "/api/v1/analytics/dashboard/",
}


class AdvisorCaseSetTests(SimpleTestCase):
    def setUp(self):
        self.case_set = json.loads(CASE_SET_PATH.read_text(encoding="utf-8"))

    def test_case_set_is_versioned_synthetic_and_provider_free(self):
        self.assertEqual(self.case_set["case_set_id"], "selleros-advisor-cases-v1")
        self.assertEqual(self.case_set["case_set_revision"], 1)
        self.assertEqual(self.case_set["provenance"], "synthetic-only")
        self.assertEqual(self.case_set["provider_call"], "NOT_AUTHORIZED")
        self.assertEqual(self.case_set["external_action"], "NONE")
        self.assertEqual(
            set(self.case_set["supported_insight_types"]), set(SUPPORTED_INSIGHTS)
        )

    def test_every_supported_insight_has_source_evidence_and_scope(self):
        seen_supported_insights = set()
        seen_case_ids = set()

        for case in self.case_set["cases"]:
            self.assertNotIn(case["case_id"], seen_case_ids)
            seen_case_ids.add(case["case_id"])
            insight_type = case["insight_type"]
            self.assertTrue(case["scope"])
            self.assertTrue(case["expected_safe_result"])

            if insight_type in SUPPORTED_INSIGHTS:
                seen_supported_insights.add(insight_type)
                self.assertEqual(
                    case["source_endpoint"], SUPPORTED_INSIGHTS[insight_type]
                )
                self.assertTrue(case["required_evidence_fields"])
            else:
                self.assertEqual(case["source_endpoint"], "none")
                self.assertEqual(case["required_evidence_fields"], [])

        self.assertEqual(seen_supported_insights, set(SUPPORTED_INSIGHTS))
