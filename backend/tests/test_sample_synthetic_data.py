"""Validation for the reviewed, static synthetic catalog/customer manifest."""
import json
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "sample"
    / "synthetic-catalog-customers.v1.json"
)


class SyntheticCatalogCustomerFixtureTests(SimpleTestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_manifest_is_fixed_and_explicitly_synthetic(self):
        self.assertEqual(
            self.fixture["fixture_id"], "selleros-synthetic-catalog-customers-v1"
        )
        self.assertEqual(self.fixture["fixture_revision"], 1)
        self.assertEqual(self.fixture["provenance"], "synthetic")
        self.assertEqual(
            self.fixture["label"], "SYNTHETIC DATA — NOT SELLER PERFORMANCE"
        )
        self.assertEqual(self.fixture["currency_code"], "BDT")

    def test_products_and_variants_are_repeatable_and_well_formed(self):
        store_keys = {store["fixture_key"] for store in self.fixture["stores"]}
        product_keys = set()
        variant_keys = set()

        for product in self.fixture["products"]:
            self.assertNotIn(product["fixture_key"], product_keys)
            product_keys.add(product["fixture_key"])
            self.assertIn(product["store_key"], store_keys)
            self.assertGreater(Decimal(product["selling_price"]), Decimal("0.00"))
            if product["unit_cost"] is not None:
                self.assertGreaterEqual(Decimal(product["unit_cost"]), Decimal("0.00"))

            variants = product["variants"]
            self.assertEqual(bool(variants), product["has_variants"])
            variant_names = set()
            for variant in variants:
                self.assertNotIn(variant["fixture_key"], variant_keys)
                variant_keys.add(variant["fixture_key"])
                self.assertNotIn(variant["name"].casefold(), variant_names)
                variant_names.add(variant["name"].casefold())

        self.assertEqual(len(store_keys), 2)
        self.assertTrue(any(not product["is_active"] for product in self.fixture["products"]))
        self.assertTrue(
            any(product["unit_cost"] is None for product in self.fixture["products"])
        )

    def test_customer_history_stubs_are_store_isolated_and_have_no_contacts(self):
        customers = {
            customer["fixture_key"]: customer for customer in self.fixture["customers"]
        }
        products = {
            product["fixture_key"]: product for product in self.fixture["products"]
        }
        history_keys = set()

        for customer in customers.values():
            self.assertTrue(customer["display_name"].startswith("Synthetic Customer "))
            self.assertIsNone(customer["email"])
            self.assertIsNone(customer["phone"])

        for history in self.fixture["customer_history_stubs"]:
            self.assertNotIn(history["fixture_key"], history_keys)
            history_keys.add(history["fixture_key"])
            customer = customers[history["customer_key"]]
            product = products[history["product_key"]]
            self.assertEqual(customer["store_key"], product["store_key"])
            self.assertEqual(history["kind"], "SYNTHETIC_PURCHASE_HISTORY_STUB")
            self.assertGreater(history["quantity"], 0)

        self.assertEqual(
            customers["customer-a-new"]["history_case"], "no_purchase_history"
        )
        self.assertTrue(history_keys)
