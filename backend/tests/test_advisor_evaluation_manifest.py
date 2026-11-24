"""Structural guard for the versioned ADVISOR-05 evaluation rubric."""
import json
from pathlib import Path

from django.test import SimpleTestCase


EVALUATION_PATH = (
    Path(__file__).resolve().parent / "advisor_cases" / "evaluation-v1.json"
)
REQUIRED_DIMENSIONS = {
    "evidence_consistency",
    "scope_and_clarity",
    "unsupported_claim_safety",
    "missing_data_disclosure",
    "failure_and_privacy_boundary",
}


class AdvisorEvaluationManifestTests(SimpleTestCase):
    def test_rubric_is_versioned_synthetic_and_bounded(self):
        evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))

        self.assertEqual(evaluation["evaluation_id"], "selleros-advisor-evaluation-v1")
        self.assertEqual(evaluation["revision"], 1)
        self.assertEqual(evaluation["provenance"], "synthetic-only")
        self.assertEqual(evaluation["provider_state"], "disabled")
        self.assertEqual(evaluation["external_action"], "NONE")

        rubric_dimensions = set()
        for criterion in evaluation["rubric"]:
            rubric_dimensions.add(criterion["dimension"])
            self.assertTrue(criterion["review_question"])
            self.assertTrue(criterion["method"])
            self.assertTrue(criterion["not_measured"])
        self.assertEqual(rubric_dimensions, REQUIRED_DIMENSIONS)

    def test_each_evaluation_case_is_traceable_to_an_automated_test(self):
        evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))

        case_ids = set()
        covered_dimensions = set()
        for case in evaluation["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            covered_dimensions.add(case["dimension"])
            self.assertIn(case["dimension"], REQUIRED_DIMENSIONS)
            self.assertTrue(case["test_reference"].startswith("apps.advisor.tests."))
            self.assertTrue(case["expected_observation"])

        self.assertEqual(covered_dimensions, REQUIRED_DIMENSIONS)
