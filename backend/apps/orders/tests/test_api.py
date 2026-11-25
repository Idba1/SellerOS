from datetime import datetime, timezone
from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class OrderReadApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="order-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="order-api-b"))
        self.customer_a = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic Buyer A"
        )
        self.customer_b = Customer.objects.create(
            store=self.graph_b.store, display_name="Synthetic Buyer B"
        )
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Order API Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Order API Product B",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.pending = self.create_order(
            store=self.graph_a.store,
            customer=self.customer_a,
            product=self.product_a,
            status=SalesOrder.Status.PENDING,
            created_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )
        self.delivered = self.create_order(
            store=self.graph_a.store,
            customer=self.customer_a,
            product=self.product_a,
            status=SalesOrder.Status.DELIVERED,
            created_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            delivered_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
        )
        self.foreign = self.create_order(
            store=self.graph_b.store,
            customer=self.customer_b,
            product=self.product_b,
            status=SalesOrder.Status.DELIVERED,
            created_at=datetime(2026, 1, 25, tzinfo=timezone.utc),
        )
        self.list_url = reverse("order-list")

    @staticmethod
    def create_order(*, store, customer, product, status, created_at, delivered_at=None):
        order = SalesOrder.objects.create(
            store=store,
            customer=customer,
            status=status,
            delivered_at=delivered_at,
            order_discount=Decimal("5.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=1,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("20.00"),
            discount_allocation=Decimal("5.00"),
        )
        SalesOrder.objects.filter(pk=order.pk).update(created_at=created_at)
        order.refresh_from_db()
        return order

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_is_paginated_filtered_by_status_date_and_store(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(
            f"{self.list_url}?status=DELIVERED&created_from=2026-01-15&created_to=2026-01-22&page_size=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["id"], str(self.delivered.pk))
        self.assertEqual(row["customer_display_name"], "Synthetic Buyer A")
        self.assertEqual(row["status"], SalesOrder.Status.DELIVERED)
        self.assertNotIn("store", row)
        self.assertNotIn(str(self.foreign.pk), str(response.data))

    def test_active_staff_can_read_same_store_detail_with_item_snapshots(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.get(reverse("order-detail", args=[self.delivered.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.delivered.pk))
        self.assertEqual(response.data["items"][0]["product_name_snapshot"], "Order API Product A")
        self.assertEqual(response.data["items"][0]["selling_price_snapshot"], "100.00")
        self.assertNotIn("store", response.data)

    def test_foreign_detail_is_not_found_without_data_disclosure(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(reverse("order-detail", args=[self.foreign.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertNotIn(str(self.foreign.pk), str(response.data))
        self.assertNotIn("Synthetic Buyer B", str(response.data))

    def test_query_and_authentication_validation_fail_closed(self):
        unauthenticated = self.client.get(self.list_url)
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthenticated.data["error"]["code"], "not_authenticated")

        self.authenticate(self.graph_a.owner)
        cases = (
            (f"{self.list_url}?status=UNKNOWN", "status"),
            (f"{self.list_url}?created_from=01-20-2026", "created_from"),
            (
                f"{self.list_url}?created_from=2026-02-01&created_to=2026-01-01",
                "created_to",
            ),
            (f"{self.list_url}?store_id={self.graph_b.store.pk}", "store_id"),
        )
        for url, field in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

    def test_owner_can_create_confirmed_order_and_stock_is_deducted(self):
        StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.product_a,
            quantity_on_hand=3,
        )
        self.authenticate(self.graph_a.owner)

        response = self.client.post(
            self.list_url,
            {
                "customer_id": str(self.customer_a.pk),
                "items": [{"product_id": str(self.product_a.pk), "quantity": 2}],
                "order_discount": "5.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], SalesOrder.Status.CONFIRMED)
        self.assertEqual(response.data["items"][0]["quantity"], 2)
        stock = StockUnit.objects.get(store=self.graph_a.store, product=self.product_a)
        self.assertEqual(stock.quantity_on_hand, 1)
