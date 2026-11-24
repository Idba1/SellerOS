from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product, ProductVariant
from tests.factories import FactoryContext, create_store_graph


class ProductApiRegressionTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="product-regression-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="product-regression-b"))
        self.list_url = reverse("product-list")
        self.product = Product.objects.create(
            store=self.graph_a.store,
            name="Retained Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def create_payload(self, **overrides):
        payload = {
            "name": "Repeatable Product",
            "selling_price": "100.00",
            "unit_cost": "20.00",
            "has_variants": False,
            "is_active": True,
        }
        payload.update(overrides)
        return payload

    def test_duplicate_product_names_are_allowed_within_the_authorized_store(self):
        self.authenticate(self.graph_a.owner)

        first = self.client.post(self.list_url, self.create_payload(), format="json")
        second = self.client.post(self.list_url, self.create_payload(), format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            Product.objects.filter(
                store=self.graph_a.store, name="Repeatable Product"
            ).count(),
            2,
        )

    def test_api_rejects_invalid_decimal_values_and_unapproved_sku_field(self):
        self.authenticate(self.graph_a.owner)
        initial_count = Product.objects.count()
        cases = (
            (self.create_payload(selling_price="-0.01"), "selling_price"),
            (self.create_payload(selling_price="0.00"), "selling_price"),
            (self.create_payload(selling_price="1.001"), "selling_price"),
            (self.create_payload(unit_cost="-0.01"), "unit_cost"),
            (self.create_payload(sku="SKU-001"), "sku"),
        )

        for payload, field in cases:
            with self.subTest(field=field, payload=payload):
                response = self.client.post(self.list_url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

        self.assertEqual(Product.objects.count(), initial_count)

    def test_inactive_product_is_retained_readable_and_filterable(self):
        self.authenticate(self.graph_a.owner)
        detail_url = reverse("product-detail", args=[self.product.id])

        deactivated = self.client.patch(
            detail_url, {"is_active": False}, format="json"
        )
        detail = self.client.get(detail_url)
        inactive_list = self.client.get(f"{self.list_url}?is_active=false")

        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data["is_active"])
        self.assertEqual(inactive_list.status_code, 200)
        self.assertIn(
            str(self.product.id),
            [item["id"] for item in inactive_list.data["results"]],
        )

    def test_variant_mode_change_is_allowed_without_variants_and_rejected_with_them(self):
        self.authenticate(self.graph_a.owner)
        response = self.client.post(
            self.list_url,
            self.create_payload(name="Variant Candidate", has_variants=True),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(pk=response.data["id"])

        without_variants = self.client.patch(
            reverse("product-detail", args=[product.id]),
            {"has_variants": False},
            format="json",
        )
        self.assertEqual(without_variants.status_code, 200)
        product.refresh_from_db()
        product.has_variants = True
        product.save()
        ProductVariant.objects.create(product=product, name="Sky")

        with_variant = self.client.patch(
            reverse("product-detail", args=[product.id]),
            {"has_variants": False},
            format="json",
        )
        self.assertEqual(with_variant.status_code, 400)
        self.assertIn("has_variants", with_variant.data["error"]["details"])

    def test_revoked_staff_cannot_read_or_write_store_products(self):
        self.graph_a.staff_membership.is_active = False
        self.graph_a.staff_membership.save()
        self.authenticate(self.graph_a.staff)

        list_response = self.client.get(self.list_url)
        create_response = self.client.post(
            self.list_url, self.create_payload(name="Revoked Attempt"), format="json"
        )
        update_response = self.client.patch(
            reverse("product-detail", args=[self.product.id]),
            {"is_active": False},
            format="json",
        )

        for response in (list_response, create_response, update_response):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data["error"]["code"], "not_found")
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)
