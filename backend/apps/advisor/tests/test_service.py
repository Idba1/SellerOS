from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID

from django.test import SimpleTestCase

from apps.advisor.context import (
    AdvisorContext,
    AdvisorCustomerContext,
    AdvisorProductContext,
    AdvisorProfitContext,
    AdvisorSalesContext,
)
from apps.advisor.schemas import validate_advisor_output
from apps.advisor.service import build_advisor_selection_prompt, generate_advisor_response
from apps.ai.providers.adapter import ProviderTransportError
from apps.ai.providers.configuration import LLMProviderPolicy
from apps.inventory.services import StockThresholdSummary


class AdvisorGenerationAndValidationTests(SimpleTestCase):
    def setUp(self):
        self.context = AdvisorContext(
            store_id=UUID("00000000-0000-0000-0000-000000000001"),
            store_timezone="Asia/Dhaka",
            sales=AdvisorSalesContext(
                period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
                delivered_order_count=2,
                delivered_units=3,
                delivered_gross_sales=Decimal("2090.00"),
                delivered_order_discounts=Decimal("0.00"),
                delivered_net_sales_before_reversals=Decimal("2090.00"),
                data_completeness_status="unknown",
                return_adjustment_status="decision_required",
            ),
            profit=AdvisorProfitContext(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                net_revenue=Decimal("270.00"),
                product_cost=Decimal("110.00"),
                seller_delivery_cost=Decimal("15.00"),
                recorded_operating_cost=Decimal("20.00"),
                estimated_operational_profit=Decimal("125.00"),
                estimated_profit_margin_percent=Decimal("46.30"),
                completeness_status="complete",
            ),
            stock=StockThresholdSummary(low_stock_count=1, configured_threshold_count=2),
            product=AdvisorProductContext(
                product_id=UUID("00000000-0000-0000-0000-000000000002"),
                delivered_units=3,
                delivered_gross_sales=Decimal("2090.00"),
                data_completeness_status="unknown",
                return_adjustment_status="decision_required",
            ),
            customer=AdvisorCustomerContext(
                customer_id=UUID("00000000-0000-0000-0000-000000000003"),
                purchase_count=2,
                last_purchase_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
                total_spend=Decimal("2090.00"),
            ),
        )

    def test_valid_selection_renders_only_existing_metrics_period_and_warnings(self):
        result = validate_advisor_output(
            self.context,
            {
                "state": "explain",
                "insight_types": [
                    "base_delivered_sales_snapshot",
                    "estimated_profit_completeness_snapshot",
                    "low_stock_threshold_snapshot",
                ],
            },
        )

        self.assertEqual(result.state, "explanation")
        self.assertIn("BDT 2090.00", result.explanation)
        self.assertIn("BDT 125.00", result.explanation)
        self.assertIn("2026-01-01", result.explanation)
        self.assertEqual(
            [item.source_endpoint for item in result.evidence],
            [
                "/api/v1/analytics/sales-summary/",
                "/api/v1/profit/summary/",
                "/api/v1/analytics/dashboard/",
            ],
        )
        self.assertEqual(
            result.evidence[0].period_kind,
            "half_open_delivery_event_interval",
        )
        self.assertEqual(result.evidence[0].period_start, "2026-01-01T00:00:00+00:00")
        self.assertEqual(result.evidence[1].period_end, "2026-01-31")
        self.assertEqual(result.evidence[2].period_kind, "current_state")
        self.assertIn("return_adjustment_status:decision_required", result.warnings)

    def test_contradictory_or_free_text_output_becomes_abstention(self):
        result = validate_advisor_output(
            self.context,
            {
                "state": "explain",
                "insight_types": ["base_delivered_sales_snapshot"],
                "explanation": "Profit is BDT 999999.00; send a discount now.",
            },
        )

        self.assertEqual(result.state, "abstain")
        self.assertIsNone(result.explanation)
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.warnings, ("invalid_provider_output",))

    def test_missing_profit_data_is_disclosed_without_numeric_profit(self):
        incomplete_context = replace(
            self.context,
            profit=replace(
                self.context.profit,
                estimated_operational_profit=None,
                estimated_profit_margin_percent=None,
                completeness_status="unavailable_missing_product_cost",
            ),
        )

        result = validate_advisor_output(
            incomplete_context,
            {
                "state": "explain",
                "insight_types": ["estimated_profit_completeness_snapshot"],
            },
        )

        self.assertEqual(result.state, "explanation")
        self.assertIn("unavailable", result.explanation)
        self.assertNotIn("125.00", result.explanation)
        self.assertIn(
            "profit_completeness_status:unavailable_missing_product_cost",
            result.warnings,
        )

    def test_disabled_or_failed_provider_returns_safe_unavailable_state(self):
        provider = Mock()
        disabled_result = generate_advisor_response(
            self.context,
            provider=provider,
            policy=self.disabled_policy(),
        )
        self.assertEqual(disabled_result.state, "unavailable")
        self.assertEqual(disabled_result.warnings, ("provider_execution_disabled",))
        provider.generate.assert_not_called()

        secret = "not-a-real-provider-key"
        provider.generate.side_effect = ProviderTransportError(secret)
        failure_result = generate_advisor_response(
            self.context,
            provider=provider,
            policy=self.enabled_test_policy(),
        )
        self.assertEqual(failure_result.state, "unavailable")
        self.assertEqual(failure_result.warnings, ("provider_unavailable",))
        self.assertNotIn(secret, str(failure_result))

    def test_prompt_contains_metrics_but_not_customer_identifiers(self):
        prompt = build_advisor_selection_prompt(self.context)

        self.assertIn("2090.00", prompt)
        self.assertIn("125.00", prompt)
        self.assertIn(str(self.context.product.product_id), prompt)
        self.assertNotIn(str(self.context.customer.customer_id), prompt)
        self.assertNotIn("purchase_count", prompt)
        self.assertIn("invoke tools", prompt)

    @staticmethod
    def disabled_policy() -> LLMProviderPolicy:
        return LLMProviderPolicy(
            provider_name=None,
            model_name=None,
            execution_enabled=False,
            request_timeout_seconds=0,
            maximum_request_cost_bdt=Decimal("0.00"),
        )

    @staticmethod
    def enabled_test_policy() -> LLMProviderPolicy:
        return LLMProviderPolicy(
            provider_name="test-only",
            model_name="test-only-model",
            execution_enabled=True,
            request_timeout_seconds=4,
            maximum_request_cost_bdt=Decimal("1.00"),
        )
