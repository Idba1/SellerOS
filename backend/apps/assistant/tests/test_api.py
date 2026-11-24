from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.assistant.models import AssistantEvaluationLog
from apps.catalog.models import Product
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class AssistantDraftApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.graph_a = create_store_graph(FactoryContext(namespace="assistant-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="assistant-api-b"))
        self.url = reverse("assistant-draft")

        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Harbor Canvas Tote",
            selling_price=Decimal("850.00"),
            unit_cost=Decimal("350.00"),
        )
        self.stock_a = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.product_a,
            quantity_on_hand=4,
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Product",
            selling_price=Decimal("999.00"),
            unit_cost=Decimal("100.00"),
        )
        self.stock_b = StockUnit.objects.create(
            store=self.graph_b.store,
            product=self.product_b,
            quantity_on_hand=9,
        )

    def authenticate(self, account):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=account).key}"
        )

    def test_authentication_and_strict_message_validation_fail_without_logging(self):
        anonymous = self.client.post(
            self.url,
            {"customer_message": "Harbor Canvas Tote"},
            format="json",
        )
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(anonymous.data["error"]["code"], "not_authenticated")

        self.authenticate(self.graph_a.owner)
        for payload, field in (
            ({"customer_message": "   "}, "customer_message"),
            ({"customer_message": "x" * 2_001}, "customer_message"),
            (
                {
                    "customer_message": "Harbor Canvas Tote",
                    "store_id": str(self.graph_b.store.pk),
                },
                "store_id",
            ),
        ):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

        self.assertEqual(AssistantEvaluationLog.objects.count(), 0)

    def test_disabled_provider_returns_safe_failure_and_logs_minimal_metadata(self):
        self.authenticate(self.graph_a.owner)
        customer_message = (
            "Contact buyer@example.test or +8801712345678. "
            "Is Harbor Canvas Tote available?"
        )

        response = self.client.post(
            self.url,
            {"customer_message": customer_message},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"]["code"], "assistant_unavailable")
        self.assertEqual(response.data["error"]["details"]["state"], "unavailable")
        self.assertEqual(
            response.data["error"]["details"]["warnings"],
            ["provider_execution_disabled"],
        )

        log = AssistantEvaluationLog.objects.get()
        self.assertEqual(log.store_id, self.graph_a.store.pk)
        self.assertEqual(log.requested_by_id, self.graph_a.owner.pk)
        self.assertEqual(
            log.outcome_state,
            AssistantEvaluationLog.OutcomeState.PROVIDER_UNAVAILABLE,
        )
        self.assertEqual(log.provider_state, "DISABLED")
        self.assertEqual(log.message_length, len(customer_message))
        self.assertTrue(log.contact_identifiers_redacted)
        self.assertEqual(log.context_fact_count, 1)
        self.assertEqual(
            {(item["source_type"], item["source_id"]) for item in log.source_metadata},
            {("product", str(self.product_a.pk)), ("stock_unit", str(self.stock_a.pk))},
        )
        self.assertEqual(log.warning_codes, ["provider_execution_disabled"])
        serialized_log = str(log.__dict__)
        self.assertNotIn(customer_message, serialized_log)
        self.assertNotIn("buyer@example.test", serialized_log)
        self.assertNotIn("+8801712345678", serialized_log)

    def test_foreign_product_never_enters_context_or_evaluation_metadata(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            self.url,
            {"customer_message": "What is the price of Foreign Product?"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        log = AssistantEvaluationLog.objects.get()
        self.assertEqual(log.store_id, self.graph_a.store.pk)
        self.assertEqual(log.context_fact_count, 0)
        self.assertEqual(log.source_metadata, [])
        self.assertNotIn(str(self.stock_b.pk), str(log.source_metadata))
        self.assertNotIn(self.product_b.name, str(log.source_metadata))

    def test_revoked_staff_cannot_request_a_draft_or_create_a_log(self):
        self.graph_a.staff_membership.is_active = False
        self.graph_a.staff_membership.save()
        self.authenticate(self.graph_a.staff)

        response = self.client.post(
            self.url,
            {"customer_message": "Harbor Canvas Tote"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertEqual(AssistantEvaluationLog.objects.count(), 0)

    @override_settings(ASSISTANT_CONTEXT_BUILD_MAX_SECONDS=2.0)
    @patch("apps.assistant.api.views.time.monotonic", side_effect=(0.0, 2.1))
    def test_context_timeout_discards_result_and_records_safe_outcome(self, _clock):
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            self.url,
            {"customer_message": "Harbor Canvas Tote"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data["error"]["details"]["warnings"],
            ["context_build_timed_out"],
        )
        log = AssistantEvaluationLog.objects.get()
        self.assertEqual(
            log.outcome_state,
            AssistantEvaluationLog.OutcomeState.CONTEXT_TIMED_OUT,
        )
        self.assertEqual(log.warning_codes, ["context_build_timed_out"])

    def test_scoped_rate_limit_blocks_before_creating_another_log(self):
        self.authenticate(self.graph_a.owner)

        responses = [
            self.client.post(
                self.url,
                {"customer_message": "Harbor Canvas Tote"},
                format="json",
            )
            for _ in range(11)
        ]

        self.assertTrue(all(response.status_code == 503 for response in responses[:10]))
        self.assertEqual(responses[-1].status_code, 429)
        self.assertEqual(responses[-1].data["error"]["code"], "throttled")
        self.assertEqual(AssistantEvaluationLog.objects.count(), 10)
