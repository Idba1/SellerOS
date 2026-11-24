from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.customers.models import Customer
from tests.factories import FactoryContext, create_store_graph


class CustomerApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="customer-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="customer-api-b"))
        self.list_url = reverse("customer-list")
        self.alpha = Customer.objects.create(
            store=self.graph_a.store,
            display_name="Alpha Buyer",
            phone="synthetic-contact-a",
            email="alpha@example.test",
        )
        self.zeta = Customer.objects.create(
            store=self.graph_a.store,
            display_name="Zeta Buyer",
        )
        self.foreign = Customer.objects.create(
            store=self.graph_b.store,
            display_name="Foreign Buyer",
            email="foreign@example.test",
        )

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_owner_list_is_paginated_ordered_and_store_scoped(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(f"{self.list_url}?page_size=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], str(self.alpha.pk))
        self.assertEqual(response.data["results"][0]["display_name"], "Alpha Buyer")
        self.assertNotIn("store", response.data["results"][0])
        self.assertNotIn(str(self.foreign.pk), str(response.data))
        self.assertIsNotNone(response.data["next"])

    def test_active_staff_can_read_same_store_detail(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.get(reverse("customer-detail", args=[self.alpha.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.alpha.pk))
        self.assertEqual(response.data["email"], "alpha@example.test")
        self.assertNotIn("store", response.data)

    def test_owner_creates_customer_with_server_resolved_store(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            self.list_url,
            {
                "display_name": "  New Buyer  ",
                "phone": "   ",
                "email": "   ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(pk=response.data["id"])
        self.assertEqual(customer.store, self.graph_a.store)
        self.assertEqual(customer.display_name, "New Buyer")
        self.assertIsNone(customer.phone)
        self.assertIsNone(customer.email)
        self.assertNotIn("store", response.data)

    def test_active_staff_updates_same_store_customer(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.patch(
            reverse("customer-detail", args=[self.alpha.pk]),
            {"display_name": "Updated Buyer", "phone": "updated-contact"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.display_name, "Updated Buyer")
        self.assertEqual(self.alpha.phone, "updated-contact")

    def test_foreign_detail_and_update_are_not_found_without_side_effects(self):
        self.authenticate(self.graph_a.owner)
        detail_url = reverse("customer-detail", args=[self.foreign.pk])

        get_response = self.client.get(detail_url)
        patch_response = self.client.patch(
            detail_url,
            {"display_name": "Attempted Foreign Update"},
            format="json",
        )

        for response in (get_response, patch_response):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data["error"]["code"], "not_found")
            self.assertNotIn(str(self.foreign.pk), str(response.data))
            self.assertNotIn("Foreign Buyer", str(response.data))

        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.display_name, "Foreign Buyer")

    def test_payload_and_query_validation_rejects_unapproved_rules(self):
        self.authenticate(self.graph_a.owner)
        detail_url = reverse("customer-detail", args=[self.alpha.pk])
        cases = (
            ("post", self.list_url, {"email": "valid@example.test"}, "display_name"),
            (
                "post",
                self.list_url,
                {"display_name": "Bad", "store_id": str(self.graph_b.store.pk)},
                "store_id",
            ),
            ("patch", detail_url, {"email": "not-an-email"}, "email"),
        )
        for method, url, payload, field in cases:
            with self.subTest(method=method, field=field):
                response = getattr(self.client, method)(url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

        response = self.client.get(f"{self.list_url}?store_id={self.graph_b.store.pk}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("store_id", response.data["error"]["details"])

    def test_unauthenticated_routes_and_delete_are_rejected(self):
        detail_url = reverse("customer-detail", args=[self.alpha.pk])
        responses = (
            self.client.get(self.list_url),
            self.client.post(
                self.list_url,
                {"display_name": "Anonymous Buyer"},
                format="json",
            ),
            self.client.get(detail_url),
            self.client.patch(
                detail_url,
                {"display_name": "Anonymous Update"},
                format="json",
            ),
        )
        for response in responses:
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.data["error"]["code"], "not_authenticated")

        self.authenticate(self.graph_a.owner)
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 405)
        self.assertEqual(delete_response.data["error"]["code"], "method_not_allowed")
