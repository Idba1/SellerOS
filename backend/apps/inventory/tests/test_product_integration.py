"""Cross-module evidence for linked catalogue products and stock units."""

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class ProductInventoryIntegrationTests(APITestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="product-inventory"))
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.graph.owner).key}"
        )

    def create_product_via_catalogue_api(self, *, name="Launch Tote"):
        response = self.client.post(
            reverse("product-list"),
            {
                "name": name,
                "category": "Carry goods",
                "selling_price": "100.00",
                "unit_cost": "20.00",
                "has_variants": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return Product.objects.get(pk=response.data["id"])

    def provision_stock_unit_for_test(self, product, *, quantity_on_hand=5):
        """Use the unit automatically created with a standalone catalogue product."""

        stock_unit = StockUnit.objects.get(store=self.graph.store, product=product)
        stock_unit.quantity_on_hand = quantity_on_hand
        stock_unit.low_stock_threshold = 2
        stock_unit.save()
        return stock_unit

    def test_catalogue_created_and_renamed_product_is_current_in_inventory_list(self):
        product = self.create_product_via_catalogue_api()
        stock_unit = self.provision_stock_unit_for_test(product)

        before_update = self.client.get(reverse("inventory-list"))
        self.assertEqual(before_update.status_code, 200)
        self.assertEqual(before_update.data["count"], 1)
        self.assertEqual(before_update.data["results"][0]["product_id"], str(product.pk))
        self.assertEqual(before_update.data["results"][0]["product_name"], "Launch Tote")

        update_response = self.client.patch(
            reverse("product-detail", args=[product.pk]),
            {"name": "Renamed Tote"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)

        inventory_response = self.client.get(reverse("inventory-list"))
        self.assertEqual(inventory_response.status_code, 200)
        row = inventory_response.data["results"][0]
        self.assertEqual(row["id"], str(stock_unit.pk))
        self.assertEqual(row["product_id"], str(product.pk))
        self.assertEqual(row["product_name"], "Renamed Tote")
        self.assertEqual(row["quantity_on_hand"], 5)
        self.assertEqual(row["low_stock_threshold"], 2)

    def test_catalogue_created_standalone_product_has_zero_balance_stock_unit(self):
        product = self.create_product_via_catalogue_api(name="Auto Stock Tote")

        stock_unit = StockUnit.objects.get(store=self.graph.store, product=product)

        self.assertEqual(stock_unit.quantity_on_hand, 0)
        self.assertIsNone(stock_unit.low_stock_threshold)

    def test_inventory_adjustment_and_history_agree_for_catalogue_product(self):
        product = self.create_product_via_catalogue_api(name="Adjustment Tote")
        stock_unit = self.provision_stock_unit_for_test(product, quantity_on_hand=5)

        adjustment_response = self.client.post(
            reverse("inventory-manual-adjustment", args=[stock_unit.pk]),
            {"quantity_delta": -2, "reason": "Damaged packaging count"},
            format="json",
        )
        self.assertEqual(adjustment_response.status_code, 201)
        movement_id = adjustment_response.data["id"]

        inventory_response = self.client.get(reverse("inventory-list"))
        self.assertEqual(inventory_response.status_code, 200)
        self.assertEqual(inventory_response.data["results"][0]["quantity_on_hand"], 3)

        history_response = self.client.get(
            reverse("inventory-movement-list", args=[stock_unit.pk])
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.data["count"], 1)
        history = history_response.data["results"][0]
        self.assertEqual(history["id"], movement_id)
        self.assertEqual(history["stock_unit_id"], str(stock_unit.pk))
        self.assertEqual(history["quantity_delta"], -2)
        self.assertEqual(history["reason"], "Damaged packaging count")
