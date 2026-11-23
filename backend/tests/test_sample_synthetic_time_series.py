"""Validation for the static DATA-03 order, expense, and chronology manifest."""
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase


SAMPLE_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "sample"
CATALOG_FIXTURE_PATH = SAMPLE_DIRECTORY / "synthetic-catalog-customers.v1.json"
TIME_SERIES_FIXTURE_PATH = SAMPLE_DIRECTORY / "synthetic-orders-expenses-timeseries.v1.json"
ALLOWED_STATUS_TRANSITIONS = {
    ("CONFIRMED", "PROCESSING"),
    ("CONFIRMED", "CANCELLED"),
    ("PROCESSING", "SHIPPED"),
    ("SHIPPED", "DELIVERED"),
    ("DELIVERED", "RETURN_REQUESTED"),
    ("RETURN_REQUESTED", "RETURNED"),
}


class SyntheticOrderExpenseTimeSeriesFixtureTests(SimpleTestCase):
    def setUp(self):
        self.catalog = json.loads(CATALOG_FIXTURE_PATH.read_text(encoding="utf-8"))
        self.fixture = json.loads(TIME_SERIES_FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_manifest_is_explicitly_synthetic_and_references_data_02(self):
        self.assertEqual(
            self.fixture["fixture_id"],
            "selleros-synthetic-orders-expenses-timeseries-v1",
        )
        self.assertEqual(self.fixture["fixture_revision"], 1)
        self.assertEqual(self.fixture["provenance"], "synthetic")
        self.assertEqual(
            self.fixture["label"], "SYNTHETIC DATA — NOT SELLER PERFORMANCE"
        )
        self.assertEqual(self.fixture["catalog_fixture_id"], self.catalog["fixture_id"])

    def test_order_cases_follow_allowed_chronology_and_reconcile(self):
        products = {
            product["fixture_key"]: product for product in self.catalog["products"]
        }
        customers = {
            customer["fixture_key"]: customer for customer in self.catalog["customers"]
        }

        for order in self.fixture["order_cases"]:
            reconciliation = order["reconciliation"]
            event_times = [
                datetime.fromisoformat(event["occurred_at"])
                for event in order["status_events"]
            ]
            statuses = [event["status"] for event in order["status_events"]]
            gross = sum(
                (
                    Decimal(line["selling_price_snapshot"]) * line["quantity"]
                    for line in order["lines"]
                ),
                start=Decimal("0.00"),
            )
            deducted_units = sum(line["quantity"] for line in order["lines"])

            self.assertEqual(event_times, sorted(event_times))
            self.assertTrue(
                all(pair in ALLOWED_STATUS_TRANSITIONS for pair in zip(statuses, statuses[1:]))
            )
            self.assertEqual(Decimal(reconciliation["order_gross"]), gross)
            self.assertEqual(Decimal(reconciliation["order_discount"]), Decimal("0.00"))
            self.assertEqual(Decimal(order["order_discount"]), Decimal("0.00"))
            self.assertEqual(reconciliation["stock_deducted_units"], deducted_units)
            self.assertEqual(customers[order["customer_key"]]["store_key"], order["store_key"])

            for line in order["lines"]:
                product = products[line["product_key"]]
                self.assertEqual(product["store_key"], order["store_key"])
                if line["variant_key"] is not None:
                    self.assertIn(
                        line["variant_key"],
                        {variant["fixture_key"] for variant in product["variants"]},
                    )

            if statuses[-1] == "DELIVERED":
                self.assertEqual(
                    Decimal(reconciliation["completed_sale_net_after_reversal"]), gross
                )
                self.assertEqual(
                    Decimal(reconciliation["net_before_reversal"]), gross
                )
                self.assertEqual(reconciliation["stock_restored_units"], 0)
            elif statuses[-1] in {"CANCELLED", "RETURNED"}:
                self.assertEqual(
                    Decimal(reconciliation["completed_sale_net_after_reversal"]),
                    Decimal("0.00"),
                )
                expected_before_reversal = (
                    gross if statuses[-1] == "RETURNED" else Decimal("0.00")
                )
                self.assertEqual(
                    Decimal(reconciliation["net_before_reversal"]),
                    expected_before_reversal,
                )
                self.assertEqual(
                    reconciliation["stock_restored_units"], deducted_units
                )

            costs = [line["unit_cost_snapshot"] for line in order["lines"]]
            if any(cost is None for cost in costs):
                self.assertIsNone(reconciliation["completed_sale_cogs_after_reversal"])
            else:
                known_cogs = sum(
                    (
                        Decimal(line["unit_cost_snapshot"]) * line["quantity"]
                        for line in order["lines"]
                    ),
                    start=Decimal("0.00"),
                )
                expected_cogs = (
                    known_cogs if statuses[-1] == "DELIVERED" else Decimal("0.00")
                )
                self.assertEqual(
                    Decimal(reconciliation["completed_sale_cogs_after_reversal"]),
                    expected_cogs,
                )

    def test_expenses_and_time_series_stubs_keep_store_boundaries(self):
        order_by_key = {
            order["fixture_key"]: order for order in self.fixture["order_cases"]
        }
        products = {
            product["fixture_key"]: product for product in self.catalog["products"]
        }
        expense_keys = set()
        series_keys = set()

        for expense in self.fixture["expense_records"]:
            self.assertNotIn(expense["fixture_key"], expense_keys)
            expense_keys.add(expense["fixture_key"])
            self.assertGreater(Decimal(expense["amount"]), Decimal("0.00"))
            datetime.fromisoformat(expense["incurred_on"])

        for series in self.fixture["chronological_series_stubs"]:
            self.assertNotIn(series["fixture_key"], series_keys)
            series_keys.add(series["fixture_key"])
            order = order_by_key[series["source_order_key"]]
            self.assertEqual(series["store_key"], order["store_key"])
            self.assertEqual(series["store_key"], products[series["product_key"]]["store_key"])
            self.assertIn(
                series["source_status"],
                [event["status"] for event in order["status_events"]],
            )
            datetime.fromisoformat(series["occurred_at"])
            self.assertGreater(series["units"], 0)

        self.assertTrue(expense_keys)
        self.assertTrue(series_keys)
