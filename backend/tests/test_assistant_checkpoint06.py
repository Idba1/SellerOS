"""Structural guard for the versioned ASSISTANT-08 evaluation checkpoint."""
import json
from pathlib import Path

from django.test import SimpleTestCase


CHECKPOINT_PATH = (
    Path(__file__).resolve().parent / "assistant_cases" / "checkpoint-06-v1.json"
)
REQUIRED_DIMENSIONS = {
    "grounding",
    "unsupported_fact_abstention",
    "prompt_injection",
    "provider_fallback",
    "context_deadline",
    "rate_limit",
}


class AssistantCheckpoint06ManifestTests(SimpleTestCase):
    def test_checkpoint_manifest_is_versioned_synthetic_and_complete(self):
        checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            checkpoint["checkpoint_id"], "selleros-assistant-checkpoint-06-v1"
        )
        self.assertEqual(checkpoint["revision"], 1)
        self.assertEqual(checkpoint["provenance"], "synthetic-only")
        self.assertEqual(checkpoint["provider_state"], "disabled")

        case_ids = set()
        dimensions = set()
        for case in checkpoint["cases"]:
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            dimensions.add(case["dimension"])
            self.assertTrue(case["test_reference"].startswith("apps."))
            self.assertTrue(case["expected_result"])

        self.assertEqual(dimensions, REQUIRED_DIMENSIONS)
