from datetime import datetime, timezone
from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class CustomerPurchaseHistoryApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="history-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="history-api-b"))
        self.customer = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic History API Buyer"
        )
        self.foreign_customer = Customer.objects.create(
            store=self.graph_b.store, display_name="Foreign History Buyer"
        )
        self.product = Product.objects.create(
            store=self.graph_a.store,
            name="History API Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        token = Token.objects.create(user=self.graph_a.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def history_url(self, customer=None):
        return reverse("customer-purchase-history", args=[(customer or self.customer).pk])

    def seed_order(self, *, status, delivered_at, quantity, price, discount=Decimal("0.00")):
        order = SalesOrder.objects.create(
            store=self.graph_a.store,
            customer=self.customer,
            status=status,
            delivered_at=delivered_at,
            order_discount=discount,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="History API Product",
            quantity=quantity,
            selling_price_snapshot=price,
            unit_cost_snapshot=Decimal("20.00"),
        )
        return order

    def test_seeded_eligible_orders_immediately_update_displayed_history_once_each(self):
        initial = self.client.get(self.history_url())
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(
            initial.data,
            {"purchase_count": 0, "last_purchase_at": None, "total_spend": "0.00"},
        )

        january = datetime(2026, 1, 10, tzinfo=timezone.utc)
        february = datetime(2026, 2, 15, tzinfo=timezone.utc)
        self.seed_order(
            status=SalesOrder.Status.DELIVERED,
            delivered_at=january,
            quantity=2,
            price=Decimal("100.00"),
            discount=Decimal("10.00"),
        )
        after_first = self.client.get(self.history_url())
        self.assertEqual(after_first.data["purchase_count"], 1)
        self.assertEqual(after_first.data["total_spend"], "190.00")
        self.assertEqual(after_first.data["last_purchase_at"], "2026-01-10T00:00:00Z")

        self.seed_order(
            status=SalesOrder.Status.RETURN_REQUESTED,
            delivered_at=february,
            quantity=1,
            price=Decimal("80.00"),
        )
        after_second = self.client.get(self.history_url())
        self.assertEqual(after_second.data["purchase_count"], 2)
        self.assertEqual(after_second.data["total_spend"], "270.00")
        self.assertEqual(after_second.data["last_purchase_at"], "2026-02-15T00:00:00Z")

        self.seed_order(
            status=SalesOrder.Status.RETURNED,
            delivered_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            quantity=1,
            price=Decimal("120.00"),
        )
        after_return = self.client.get(self.history_url())
        self.assertEqual(after_return.data, after_second.data)

    def test_foreign_customer_history_is_not_found_without_disclosure(self):
        response = self.client.get(self.history_url(self.foreign_customer))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertNotIn(str(self.foreign_customer.pk), str(response.data))
        self.assertNotIn("Foreign History Buyer", str(response.data))

    def test_unauthenticated_history_is_rejected(self):
        self.client.credentials()

        response = self.client.get(self.history_url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")

    def test_query_parameters_are_rejected(self):
        response = self.client.get(f"{self.history_url()}?store_id={self.graph_b.store.pk}")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("store_id", response.data["error"]["details"])
