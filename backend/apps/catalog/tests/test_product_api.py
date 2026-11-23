from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product, ProductVariant
from tests.factories import FactoryContext, create_store_graph


class ProductReadApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="products-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="products-b"))
        self.list_url = reverse("product-list")

        self.alpha = self.create_product(
            self.graph_a.store,
            name="Alpha Tote",
            category="Carry goods",
        )
        self.canvas = self.create_product(
            self.graph_a.store,
            name="Canvas Pouch",
            category="Carry goods",
            is_active=False,
        )
        self.zebra = self.create_product(
            self.graph_a.store,
            name="Zebra Organizer",
            category="Workspace",
            has_variants=True,
        )
        self.sky = ProductVariant.objects.create(product=self.zebra, name="Sky")
        self.foreign = self.create_product(
            self.graph_b.store,
            name="Foreign Product",
            category="Carry goods",
        )

    @staticmethod
    def create_product(store, **overrides):
        values = {
            "store": store,
            "name": "Product",
            "selling_price": Decimal("100.00"),
            "unit_cost": Decimal("20.00"),
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_owner_list_is_paginated_filtered_ordered_and_store_scoped(self):
        self.authenticate(self.graph_a.owner)

        list_response = self.client.get(f"{self.list_url}?page_size=2&ordering=name")
        filtered_response = self.client.get(
            f"{self.list_url}?category=carry%20goods&is_active=true"
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 3)
        self.assertEqual(
            [item["name"] for item in list_response.data["results"]],
            ["Alpha Tote", "Canvas Pouch"],
        )
        self.assertNotIn(str(self.foreign.id), str(list_response.data))
        self.assertEqual(filtered_response.status_code, 200)
        self.assertEqual(filtered_response.data["count"], 1)
        self.assertEqual(filtered_response.data["results"][0]["id"], str(self.alpha.id))

    def test_active_staff_can_read_same_store_detail_with_own_variants(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.get(reverse("product-detail", args=[self.zebra.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.zebra.id))
        self.assertEqual(response.data["variants"][0]["id"], str(self.sky.id))
        self.assertNotIn("store", response.data)
        self.assertNotIn("store_id", response.data)

    def test_foreign_detail_is_not_found_without_data_disclosure(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(reverse("product-detail", args=[self.foreign.id]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertNotIn(str(self.foreign.id), str(response.data))
        self.assertNotIn(self.foreign.name, str(response.data))

    def test_query_validation_rejects_store_selector_and_invalid_filters(self):
        self.authenticate(self.graph_a.owner)

        cases = (
            (f"{self.list_url}?store_id={self.graph_b.store.id}", "store_id"),
            (f"{self.list_url}?is_active=maybe", "is_active"),
            (f"{self.list_url}?ordering=selling_price", "ordering"),
            (f"{self.list_url}?category=%20%20", "category"),
            (f"{self.list_url}?category=a&category=b", "category"),
        )
        for url, field in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

    def test_unauthenticated_list_is_rejected(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
