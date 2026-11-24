from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.expenses.models import Expense
from tests.factories import FactoryContext, create_store_graph


class ExpenseApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="expense-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="expense-api-b"))
        self.today = timezone.localdate(timezone=ZoneInfo(self.graph_a.store.timezone))
        self.packaging = Expense.objects.create(
            store=self.graph_a.store,
            description="Synthetic packaging supplies",
            category="Packaging",
            amount=Decimal("100.00"),
            incurred_on=self.today - timedelta(days=2),
            recorded_by=self.graph_a.owner,
        )
        self.marketing = Expense.objects.create(
            store=self.graph_a.store,
            description="Synthetic promotion",
            category="Marketing",
            amount=Decimal("250.00"),
            incurred_on=self.today - timedelta(days=1),
            recorded_by=self.graph_a.owner,
        )
        self.foreign = Expense.objects.create(
            store=self.graph_b.store,
            description="Foreign synthetic expense",
            category="Packaging",
            amount=Decimal("300.00"),
            incurred_on=self.today - timedelta(days=1),
            recorded_by=self.graph_b.owner,
        )
        self.list_url = reverse("expense-list")

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def detail_url(self, expense):
        return reverse("expense-detail", args=[expense.pk])

    def test_list_is_store_scoped_paginated_and_filterable(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(
            f"{self.list_url}?category=packaging&incurred_from={self.today - timedelta(days=3)}&incurred_to={self.today - timedelta(days=1)}&page_size=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["id"], str(self.packaging.pk))
        self.assertEqual(row["amount"], "100.00")
        self.assertNotIn("store", row)
        self.assertNotIn(str(self.foreign.pk), str(response.data))

    def test_staff_can_create_and_update_same_store_expense(self):
        self.authenticate(self.graph_a.staff)
        create_response = self.client.post(
            self.list_url,
            {
                "description": "  Synthetic courier material  ",
                "category": "  Packaging  ",
                "amount": "99.50",
                "incurred_on": str(self.today),
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["description"], "Synthetic courier material")
        self.assertEqual(create_response.data["category"], "Packaging")
        expense = Expense.objects.get(pk=create_response.data["id"])
        self.assertEqual(expense.store, self.graph_a.store)
        self.assertEqual(expense.recorded_by, self.graph_a.staff)

        update_response = self.client.patch(
            self.detail_url(expense),
            {"amount": "120.00", "description": "Corrected synthetic material"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["amount"], "120.00")
        expense.refresh_from_db()
        self.assertEqual(expense.recorded_by, self.graph_a.staff)

    def test_same_store_detail_and_foreign_access_fail_closed(self):
        self.authenticate(self.graph_a.owner)

        detail_response = self.client.get(self.detail_url(self.marketing))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["id"], str(self.marketing.pk))

        foreign_read = self.client.get(self.detail_url(self.foreign))
        foreign_update = self.client.patch(
            self.detail_url(self.foreign),
            {"amount": "1.00"},
            format="json",
        )
        self.assertEqual(foreign_read.status_code, 404)
        self.assertEqual(foreign_update.status_code, 404)
        self.assertNotIn(str(self.foreign.pk), str(foreign_read.data))
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.amount, Decimal("300.00"))

    def test_authentication_query_and_payload_validation_fail_closed(self):
        unauthenticated = self.client.get(self.list_url)
        self.assertEqual(unauthenticated.status_code, 401)

        self.authenticate(self.graph_a.owner)
        cases = (
            (f"{self.list_url}?category=", "category"),
            (f"{self.list_url}?incurred_from=2026-99-99", "incurred_from"),
            (
                f"{self.list_url}?incurred_from={self.today}&incurred_to={self.today - timedelta(days=1)}",
                "incurred_to",
            ),
            (f"{self.list_url}?store_id={self.graph_b.store.pk}", "store_id"),
        )
        for url, field in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

        invalid_amount = self.client.post(
            self.list_url,
            {
                "description": "Synthetic invalid expense",
                "category": "Operations",
                "amount": "0.00",
                "incurred_on": str(self.today),
            },
            format="json",
        )
        self.assertEqual(invalid_amount.status_code, 400)
        self.assertEqual(invalid_amount.data["error"]["code"], "validation_error")
        self.assertIn("amount", invalid_amount.data["error"]["details"])

        forbidden_ownership_field = self.client.post(
            self.list_url,
            {
                "description": "Synthetic invalid expense",
                "category": "Operations",
                "amount": "20.00",
                "incurred_on": str(self.today),
                "store_id": str(self.graph_b.store.pk),
            },
            format="json",
        )
        self.assertEqual(forbidden_ownership_field.status_code, 400)
        self.assertEqual(
            forbidden_ownership_field.data["error"]["code"], "validation_error"
        )
        self.assertIn(
            "store_id", forbidden_ownership_field.data["error"]["details"]
        )
