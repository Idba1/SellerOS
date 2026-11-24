import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = REPOSITORY_ROOT / "docs" / "metrics.md"
TIME_SERIES_FIXTURE_PATH = (
    REPOSITORY_ROOT / "data" / "sample" / "synthetic-orders-expenses-timeseries.v1.json"
)


class SalesMetricContractTests(SimpleTestCase):
    def setUp(self):
        self.metrics = METRICS_PATH.read_text(encoding="utf-8")
        self.fixture = json.loads(TIME_SERIES_FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_document_preserves_required_sales_metric_boundaries(self):
        required_phrases = (
            "original `OrderStatusEvent` whose `to_status` is `DELIVERED`",
            "Store.timezone",
            "retained_net_sales",
            "decision_required",
            "Declared complete coverage; no eligible delivery events",
            "[DECISION REQUIRED] DR-06 / AC-01",
            "[DECISION REQUIRED] DR-07",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.metrics)

    def test_store_a_hand_calculated_base_sales_example_matches_fixture(self):
        period_start = datetime.fromisoformat("2026-01-01T00:00:00+06:00")
        period_end = datetime.fromisoformat("2026-02-28T23:59:59+06:00")
        included_orders = []
        for order in self.fixture["order_cases"]:
            if order["store_key"] != "synthetic-store-a":
                continue
            delivered_event = next(
                (
                    event
                    for event in order["status_events"]
                    if event["status"] == "DELIVERED"
                ),
                None,
            )
            if delivered_event is None:
                continue
            delivered_at = datetime.fromisoformat(delivered_event["occurred_at"])
            if period_start <= delivered_at <= period_end:
                included_orders.append(order)

        gross = sum(
            (
                Decimal(line["selling_price_snapshot"]) * line["quantity"]
                for order in included_orders
                for line in order["lines"]
            ),
            start=Decimal("0.00"),
        )
        discounts = sum(
            (Decimal(order["order_discount"]) for order in included_orders),
            start=Decimal("0.00"),
        )
        units = sum(
            (line["quantity"] for order in included_orders for line in order["lines"]),
            start=0,
        )

        self.assertEqual(len(included_orders), 2)
        self.assertEqual(units, 3)
        self.assertEqual(gross, Decimal("2090.00"))
        self.assertEqual(discounts, Decimal("0.00"))
        self.assertEqual(gross - discounts, Decimal("2090.00"))
