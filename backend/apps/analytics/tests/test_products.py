from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.analytics.services.products import summarize_product_performance
from apps.catalog.models import Product
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class ProductPerformanceServiceTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="product-performance"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.first_product = Product.objects.create(
            store=self.graph.store,
            name="Performance First Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.second_product = Product.objects.create(
            store=self.graph.store,
            name="Performance Second Product",
            selling_price=Decimal("50.00"),
            unit_cost=Decimal("20.00"),
        )

    def create_delivered_order(self, product, quantity, price, delivered_at):
        order = SalesOrder.objects.create(
            store=self.graph.store,
            status=SalesOrder.Status.RETURNED,
            delivered_at=delivered_at,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=quantity,
            selling_price_snapshot=price,
            unit_cost_snapshot=product.unit_cost,
        )
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivered_at)

    def test_product_totals_reconcile_to_delivered_order_line_snapshots(self):
        self.create_delivered_order(
            self.first_product,
            2,
            Decimal("100.00"),
            datetime(2026, 1, 10, tzinfo=self.tz),
        )
        self.create_delivered_order(
            self.first_product,
            1,
            Decimal("150.00"),
            datetime(2026, 1, 20, tzinfo=self.tz),
        )
        self.create_delivered_order(
            self.second_product,
            3,
            Decimal("50.00"),
            datetime(2026, 1, 21, tzinfo=self.tz),
        )

        summary = summarize_product_performance(
            store=self.graph.store,
            period_start=datetime(2026, 1, 1, tzinfo=self.tz),
            period_end=datetime(2026, 2, 1, tzinfo=self.tz),
        )

        by_product = {row.product_id: row for row in summary.products}
        self.assertEqual(by_product[self.first_product.pk].delivered_units, 3)
        self.assertEqual(
            by_product[self.first_product.pk].delivered_gross_sales,
            Decimal("350.00"),
        )
        self.assertEqual(by_product[self.second_product.pk].delivered_units, 3)
        self.assertEqual(
            by_product[self.second_product.pk].delivered_gross_sales,
            Decimal("150.00"),
        )
        self.assertEqual(summary.return_adjustment_status, "decision_required")
