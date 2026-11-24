from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.analytics.services.sales import SalesAggregationError, summarize_base_delivered_sales
from apps.catalog.models import Product
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class SalesAggregationServiceTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="analytics-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="analytics-b"))
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Analytics Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_a_second = Product.objects.create(
            store=self.graph_a.store,
            name="Analytics Product A Second",
            selling_price=Decimal("50.00"),
            unit_cost=Decimal("20.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Analytics Product B",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("80.00"),
        )
        self.tz = ZoneInfo("Asia/Dhaka")

    def create_order_with_delivery(
        self,
        *,
        store,
        product_lines,
        delivered_at,
        status=SalesOrder.Status.DELIVERED,
        discount=Decimal("0.00"),
    ):
        order = SalesOrder.objects.create(
            store=store,
            status=status,
            order_discount=discount,
            delivered_at=delivered_at,
        )
        for product, quantity, price in product_lines:
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
            initiated_by=store.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivered_at)
        return order

    def period(self, start, end):
        return {
            "store": self.graph_a.store,
            "period_start": datetime(*start, tzinfo=self.tz),
            "period_end": datetime(*end, tzinfo=self.tz),
        }

    def test_summary_matches_hand_calculation_and_uses_delivery_evidence(self):
        self.create_order_with_delivery(
            store=self.graph_a.store,
            product_lines=[
                (self.product_a, 2, Decimal("100.00")),
                (self.product_a_second, 1, Decimal("50.00")),
            ],
            delivered_at=datetime(2026, 1, 10, 10, 0, tzinfo=self.tz),
            discount=Decimal("10.00"),
        )
        self.create_order_with_delivery(
            store=self.graph_a.store,
            product_lines=[(self.product_a, 1, Decimal("200.00"))],
            delivered_at=datetime(2026, 2, 5, 9, 0, tzinfo=self.tz),
            status=SalesOrder.Status.RETURNED,
        )
        self.create_order_with_delivery(
            store=self.graph_b.store,
            product_lines=[(self.product_b, 1, Decimal("200.00"))],
            delivered_at=datetime(2026, 1, 12, 10, 0, tzinfo=self.tz),
        )
        SalesOrder.objects.create(store=self.graph_a.store, status=SalesOrder.Status.PENDING)

        summary = summarize_base_delivered_sales(
            **self.period((2026, 1, 1), (2026, 3, 1))
        )

        self.assertEqual(summary.delivered_order_count, 2)
        self.assertEqual(summary.delivered_units, 4)
        self.assertEqual(summary.delivered_gross_sales, Decimal("450.00"))
        self.assertEqual(summary.delivered_order_discounts, Decimal("10.00"))
        self.assertEqual(
            summary.delivered_net_sales_before_reversals, Decimal("440.00")
        )
        self.assertEqual(summary.data_completeness_status, "unknown")
        self.assertEqual(summary.return_adjustment_status, "decision_required")
        self.assertEqual(len(summary.products), 2)
        by_product = {row.product_id: row for row in summary.products}
        self.assertEqual(by_product[self.product_a.pk].delivered_units, 3)
        self.assertEqual(
            by_product[self.product_a.pk].delivered_gross_sales, Decimal("400.00")
        )
        self.assertEqual(by_product[self.product_a_second.pk].delivered_units, 1)
        self.assertEqual(
            by_product[self.product_a_second.pk].delivered_gross_sales,
            Decimal("50.00"),
        )

    def test_empty_and_invalid_periods_are_explicit(self):
        summary = summarize_base_delivered_sales(
            **self.period((2026, 4, 1), (2026, 5, 1))
        )
        self.assertEqual(summary.delivered_order_count, 0)
        self.assertEqual(summary.delivered_units, 0)
        self.assertEqual(summary.delivered_gross_sales, Decimal("0.00"))
        self.assertEqual(summary.delivered_net_sales_before_reversals, Decimal("0.00"))
        self.assertEqual(summary.data_completeness_status, "unknown")

        with self.assertRaises(SalesAggregationError):
            summarize_base_delivered_sales(
                store=self.graph_a.store,
                period_start=datetime(2026, 4, 1),
                period_end=datetime(2026, 5, 1),
            )
        with self.assertRaises(SalesAggregationError):
            summarize_base_delivered_sales(
                **self.period((2026, 5, 1), (2026, 4, 1))
            )

    def test_duplicate_delivery_evidence_fails_closed(self):
        order = self.create_order_with_delivery(
            store=self.graph_a.store,
            product_lines=[(self.product_a, 1, Decimal("100.00"))],
            delivered_at=datetime(2026, 1, 10, 10, 0, tzinfo=self.tz),
        )
        duplicate = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.RETURN_REQUESTED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph_a.owner,
        )
        OrderStatusEvent.objects.filter(pk=duplicate.pk).update(
            occurred_at=datetime(2026, 1, 11, 10, 0, tzinfo=self.tz)
        )

        with self.assertRaises(SalesAggregationError):
            summarize_base_delivered_sales(
                **self.period((2026, 1, 1), (2026, 2, 1))
            )
