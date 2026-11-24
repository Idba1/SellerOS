from datetime import datetime, timezone
from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.customers.services import get_customer_purchase_history
from apps.orders.models import OrderItem, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class CustomerPurchaseHistoryTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="customer-history"))
        self.customer = Customer.objects.create(
            store=self.graph.store, display_name="Synthetic History Buyer"
        )
        self.other_customer = Customer.objects.create(
            store=self.graph.store, display_name="Other Synthetic Buyer"
        )
        self.product = Product.objects.create(
            store=self.graph.store,
            name="History Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )

    def record_order(
        self,
        *,
        customer,
        status,
        delivered_at,
        quantity=1,
        price=Decimal("100.00"),
        discount=Decimal("0.00"),
    ):
        order = SalesOrder.objects.create(
            store=self.graph.store,
            customer=customer,
            status=status,
            delivered_at=delivered_at,
            order_discount=discount,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="History Product",
            quantity=quantity,
            selling_price_snapshot=price,
            unit_cost_snapshot=Decimal("20.00"),
        )
        return order

    def test_hand_calculated_history_uses_currently_eligible_recorded_orders(self):
        january = datetime(2026, 1, 10, tzinfo=timezone.utc)
        february = datetime(2026, 2, 15, tzinfo=timezone.utc)
        march = datetime(2026, 3, 20, tzinfo=timezone.utc)
        april = datetime(2026, 4, 2, tzinfo=timezone.utc)

        self.record_order(
            customer=self.customer,
            status=SalesOrder.Status.DELIVERED,
            delivered_at=january,
            quantity=2,
            price=Decimal("100.00"),
            discount=Decimal("10.00"),
        )
        self.record_order(
            customer=self.customer,
            status=SalesOrder.Status.RETURN_REQUESTED,
            delivered_at=february,
            quantity=1,
            price=Decimal("80.00"),
        )
        self.record_order(
            customer=self.customer,
            status=SalesOrder.Status.RETURNED,
            delivered_at=march,
            quantity=1,
            price=Decimal("120.00"),
        )
        self.record_order(
            customer=self.customer,
            status=SalesOrder.Status.REFUNDED,
            delivered_at=april,
            quantity=1,
            price=Decimal("75.00"),
        )
        self.record_order(
            customer=self.customer,
            status=SalesOrder.Status.PENDING,
            delivered_at=None,
            quantity=1,
            price=Decimal("60.00"),
        )
        self.record_order(
            customer=self.other_customer,
            status=SalesOrder.Status.DELIVERED,
            delivered_at=april,
            quantity=1,
            price=Decimal("500.00"),
        )
        self.product.selling_price = Decimal("999.00")
        self.product.save()

        history = get_customer_purchase_history(self.customer)

        self.assertEqual(history.purchase_count, 2)
        self.assertEqual(history.last_purchase_at, february)
        self.assertEqual(history.total_spend, Decimal("270.00"))

    def test_customer_without_eligible_orders_has_no_invented_history(self):
        history = get_customer_purchase_history(self.customer)

        self.assertEqual(history.purchase_count, 0)
        self.assertIsNone(history.last_purchase_at)
        self.assertEqual(history.total_spend, Decimal("0.00"))
