from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.catalog.models import Product
from apps.forecast.audit import ForecastDataAuditError, audit_store_delivery_history
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class ForecastDataAuditTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="forecast-audit-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="forecast-audit-b"))
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Forecast Audit Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_a.store,
            name="Forecast Audit Product B",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("80.00"),
        )
        self.foreign_product = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Forecast Product",
            selling_price=Decimal("300.00"),
            unit_cost=Decimal("120.00"),
        )
        self.tz = ZoneInfo("Asia/Dhaka")

    def create_delivered_order(
        self, *, store, product=None, occurred_at, status=SalesOrder.Status.DELIVERED
    ):
        order = SalesOrder.objects.create(store=store, status=status, delivered_at=occurred_at)
        if product is not None:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name_snapshot=product.name,
                quantity=1,
                selling_price_snapshot=product.selling_price,
                unit_cost_snapshot=product.unit_cost,
            )
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=store.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=occurred_at)
        return order

    def test_audit_reports_span_gaps_products_duplicates_returns_and_limitations(self):
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            occurred_at=datetime(2026, 1, 1, 10, tzinfo=self.tz),
        )
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            occurred_at=datetime(2026, 1, 3, 10, tzinfo=self.tz),
            status=SalesOrder.Status.RETURN_REQUESTED,
        )
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_b,
            occurred_at=datetime(2026, 1, 3, 15, tzinfo=self.tz),
            status=SalesOrder.Status.RETURNED,
        )
        duplicate_order = self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            occurred_at=datetime(2026, 1, 2, 10, tzinfo=self.tz),
        )
        duplicate = OrderStatusEvent.objects.create(
            order=duplicate_order,
            from_status=SalesOrder.Status.RETURN_REQUESTED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph_a.owner,
        )
        OrderStatusEvent.objects.filter(pk=duplicate.pk).update(
            occurred_at=datetime(2026, 1, 4, 10, tzinfo=self.tz)
        )
        self.create_delivered_order(
            store=self.graph_a.store,
            occurred_at=datetime(2026, 1, 5, 10, tzinfo=self.tz),
        )
        self.create_delivered_order(
            store=self.graph_b.store,
            product=self.foreign_product,
            occurred_at=datetime(2026, 1, 2, 10, tzinfo=self.tz),
        )

        audit = audit_store_delivery_history(store=self.graph_a.store)

        self.assertEqual(audit.source, "original_delivered_status_events")
        self.assertEqual(audit.raw_delivery_event_count, 6)
        self.assertEqual(audit.unique_delivery_order_count, 5)
        self.assertEqual(audit.valid_delivery_event_count, 4)
        self.assertEqual(audit.duplicate_delivery_order_count, 1)
        self.assertEqual(str(audit.date_span_start), "2026-01-01")
        self.assertEqual(str(audit.date_span_end), "2026-01-05")
        self.assertEqual(audit.calendar_day_count, 5)
        self.assertEqual(audit.days_with_valid_deliveries, 3)
        self.assertEqual(audit.gap_day_count, 2)
        self.assertEqual(
            [(str(gap.start_date), str(gap.end_date)) for gap in audit.gap_ranges],
            [("2026-01-02", "2026-01-02"), ("2026-01-04", "2026-01-04")],
        )
        self.assertEqual(audit.products_with_valid_delivery_count, 2)
        self.assertEqual(audit.valid_delivery_orders_without_items_count, 1)
        self.assertEqual(audit.return_requested_order_count, 1)
        self.assertEqual(audit.returned_or_refunded_order_count, 1)
        self.assertFalse(audit.forecast_training_permitted)
        self.assertEqual(
            audit.limitation_codes,
            (
                "history_coverage_unknown",
                "current_audit_does_not_authorize_forecast_training",
                "duplicate_delivery_evidence",
                "calendar_gaps_present",
                "delivered_orders_without_items",
                "return_treatment_not_approved_for_forecast_series",
            ),
        )

    def test_empty_store_and_invalid_store_are_explicit(self):
        audit = audit_store_delivery_history(store=self.graph_a.store)

        self.assertEqual(audit.raw_delivery_event_count, 0)
        self.assertIsNone(audit.date_span_start)
        self.assertIsNone(audit.date_span_end)
        self.assertEqual(audit.calendar_day_count, 0)
        self.assertEqual(audit.gap_ranges, ())
        self.assertEqual(audit.products_with_valid_delivery_count, 0)
        self.assertIn("no_valid_delivery_events", audit.limitation_codes)
        self.assertFalse(audit.forecast_training_permitted)

        with self.assertRaisesMessage(
            ForecastDataAuditError, "A server-resolved store is required."
        ):
            audit_store_delivery_history(store=object())
