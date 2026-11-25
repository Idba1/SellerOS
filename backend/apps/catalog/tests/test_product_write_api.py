from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class ProductWriteApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="product-writes-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="product-writes-b"))
        self.list_url = reverse("product-list")
        self.own_product = Product.objects.create(
            store=self.graph_a.store,
            name="Own Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("30.00"),
        )
        self.variant_product = Product.objects.create(
            store=self.graph_a.store,
            name="Variant Product",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("90.00"),
            has_variants=True,
        )
        ProductVariant.objects.create(product=self.variant_product, name="Sky")
        self.foreign_product = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("30.00"),
        )

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_owner_creates_product_with_server_derived_store(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            self.list_url,
            {
                "name": " Created Product ",
                "category": " Carry goods ",
                "selling_price": "850.00",
                "unit_cost": "430.00",
                "has_variants": False,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.store, self.graph_a.store)
        self.assertEqual(product.name, "Created Product")
        self.assertEqual(product.category, "Carry goods")
        stock_unit = StockUnit.objects.get(product=product)
        self.assertEqual(stock_unit.store, self.graph_a.store)
        self.assertEqual(stock_unit.quantity_on_hand, 0)
        self.assertNotIn("store", response.data)
        self.assertNotIn("store_id", response.data)

    def test_active_staff_can_update_and_deactivate_same_store_product(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.patch(
            reverse("product-detail", args=[self.own_product.id]),
            {"name": "Updated Product", "is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.own_product.refresh_from_db()
        self.assertEqual(self.own_product.name, "Updated Product")
        self.assertFalse(self.own_product.is_active)

    def test_foreign_product_update_is_not_found_and_has_no_side_effect(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.patch(
            reverse("product-detail", args=[self.foreign_product.id]),
            {"selling_price": "999.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.foreign_product.refresh_from_db()
        self.assertEqual(self.foreign_product.selling_price, Decimal("100.00"))
        self.assertNotIn(str(self.foreign_product.id), str(response.data))

    def test_write_payload_validation_rejects_invalid_values_and_store_selector(self):
        self.authenticate(self.graph_a.owner)
        detail_url = reverse("product-detail", args=[self.own_product.id])
        cases = (
            (self.list_url, {"name": "Bad", "selling_price": "0.00"}, "selling_price"),
            (detail_url, {"unit_cost": "-0.01"}, "unit_cost"),
            (self.list_url, {"name": "Bad", "selling_price": "1.00", "store_id": str(self.graph_b.store.id)}, "store_id"),
            (reverse("product-detail", args=[self.variant_product.id]), {"has_variants": False}, "has_variants"),
        )

        for url, payload, field in cases:
            with self.subTest(url=url, field=field):
                method = self.client.post if url == self.list_url else self.client.patch
                response = method(url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

    def test_unauthenticated_writes_are_rejected(self):
        create_response = self.client.post(
            self.list_url,
            {"name": "Anonymous", "selling_price": "100.00"},
            format="json",
        )
        update_response = self.client.patch(
            reverse("product-detail", args=[self.own_product.id]),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(create_response.status_code, 401)
        self.assertEqual(update_response.status_code, 401)
        self.assertEqual(create_response.data["error"]["code"], "not_authenticated")
        self.assertEqual(update_response.data["error"]["code"], "not_authenticated")

    def test_owner_adds_variant_and_receives_zero_balance_variant_stock_unit(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            reverse("product-variant-list", args=[self.variant_product.id]),
            {"name": "Navy", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        variant = ProductVariant.objects.get(pk=response.data["id"])
        stock_unit = StockUnit.objects.get(product=self.variant_product, variant=variant)
        self.assertEqual(stock_unit.store, self.graph_a.store)
        self.assertEqual(stock_unit.quantity_on_hand, 0)
