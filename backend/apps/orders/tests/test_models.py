from datetime import datetime, timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class SalesOrderModelTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="orders-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="orders-b"))
        self.customer_a = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic Buyer A"
        )
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Synthetic Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Synthetic Product B",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )

    def create_order(self, **overrides):
        values = {
            "store": self.graph_a.store,
            "customer": self.customer_a,
            "status": SalesOrder.Status.DELIVERED,
            "delivered_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return SalesOrder.objects.create(**values)

    def test_order_requires_same_store_customer_and_bdt(self):
        order = self.create_order()
        self.assertEqual(order.customer, self.customer_a)

        foreign_customer = Customer.objects.create(
            store=self.graph_b.store, display_name="Foreign Buyer"
        )
        with self.assertRaises(ValidationError):
            self.create_order(customer=foreign_customer)
        with self.assertRaises(ValidationError):
            self.create_order(currency_code="USD")

    def test_item_uses_snapshots_and_requires_same_store_product(self):
        order = self.create_order()
        item = OrderItem.objects.create(
            order=order,
            product=self.product_a,
            product_name_snapshot="Synthetic Product A",
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("20.00"),
        )
        self.assertEqual(item.order, order)
        self.assertEqual(order.items.get(pk=item.pk), item)

        with self.assertRaises(ValidationError):
            OrderItem.objects.create(
                order=order,
                product=self.product_b,
                product_name_snapshot="Synthetic Product B",
                quantity=1,
                selling_price_snapshot=Decimal("100.00"),
            )
