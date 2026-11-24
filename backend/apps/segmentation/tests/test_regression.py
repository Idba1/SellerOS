"""SEGMENT-05 regression coverage for deterministic edge-case assignments."""
from datetime import datetime, timezone
from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from apps.segmentation.service import CustomerSegment, calculate_customer_segment
from tests.factories import FactoryContext, create_store_graph


class SegmentRegressionTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="segment-regression"))
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Synthetic Segment Regression Product",
            selling_price=Decimal("5000.00"),
            unit_cost=Decimal("100.00"),
        )
        self.as_of = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)

    def create_customer(self, label):
        return Customer.objects.create(
            store=self.graph.store,
            display_name=f"Synthetic {label} Buyer",
        )

    def record_order(self, *, customer, delivered_at, price):
        order = SalesOrder.objects.create(
            store=self.graph.store,
            customer=customer,
            status=SalesOrder.Status.DELIVERED,
            delivered_at=delivered_at,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Synthetic Segment Regression Product",
            quantity=1,
            selling_price_snapshot=price,
            unit_cost_snapshot=Decimal("100.00"),
        )

    def assignment_for(self, customer):
        return calculate_customer_segment(
            store=self.graph.store,
            customer=customer,
            as_of=self.as_of,
        )

    def test_sparse_threshold_and_precedence_cases_have_expected_assignment_and_reason(self):
        no_orders = self.create_customer("No Orders")

        new = self.create_customer("New")
        self.record_order(
            customer=new,
            delivered_at=datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
            price=Decimal("500.00"),
        )

        repeat = self.create_customer("Repeat")
        self.record_order(
            customer=repeat,
            delivered_at=datetime(2026, 6, 20, 12, tzinfo=timezone.utc),
            price=Decimal("5000.00"),
        )
        self.record_order(
            customer=repeat,
            delivered_at=datetime(2026, 6, 30, 12, tzinfo=timezone.utc),
            price=Decimal("4999.99"),
        )

        high_value = self.create_customer("High Value")
        tied_delivery = datetime(2026, 6, 30, 12, tzinfo=timezone.utc)
        self.record_order(
            customer=high_value,
            delivered_at=tied_delivery,
            price=Decimal("5000.00"),
        )
        self.record_order(
            customer=high_value,
            delivered_at=tied_delivery,
            price=Decimal("5000.00"),
        )

        inactive = self.create_customer("Inactive")
        self.record_order(
            customer=inactive,
            delivered_at=datetime(2026, 3, 31, 12, tzinfo=timezone.utc),
            price=Decimal("6000.00"),
        )
        self.record_order(
            customer=inactive,
            delivered_at=datetime(2026, 4, 1, 12, tzinfo=timezone.utc),
            price=Decimal("6000.00"),
        )

        cases = (
            (
                no_orders,
                CustomerSegment.NO_RECORDED_ELIGIBLE_PURCHASE,
                "No eligible purchase is recorded in this store ledger as of the selected time. "
                "This does not establish lifetime or new-customer status.",
            ),
            (
                new,
                CustomerSegment.NEW,
                "One eligible recorded purchase occurred 30 local calendar days ago, within "
                "the 30-day new-customer window.",
            ),
            (
                repeat,
                CustomerSegment.REPEAT,
                "2 eligible recorded purchases are within the active 90-day window; trailing "
                "365-day merchandise spend is BDT 9999.99, below the high-value threshold.",
            ),
            (
                high_value,
                CustomerSegment.HIGH_VALUE,
                "2 eligible recorded purchases and BDT 10000.00 in trailing 365-day "
                "merchandise spend meet the active high-value rule.",
            ),
            (
                inactive,
                CustomerSegment.INACTIVE,
                "The most recent eligible recorded purchase was 91 local calendar days ago, "
                "outside the 90-day active window.",
            ),
        )
        for customer, expected_segment, expected_explanation in cases:
            with self.subTest(customer=customer.pk):
                assignment = self.assignment_for(customer)
                self.assertEqual(assignment.segment, expected_segment)
                self.assertEqual(assignment.explanation, expected_explanation)

    def test_tied_delivery_history_is_stable_across_repeated_calculation(self):
        customer = self.create_customer("Tied History")
        tied_delivery = datetime(2026, 6, 30, 18, 30, tzinfo=timezone.utc)
        self.record_order(
            customer=customer,
            delivered_at=tied_delivery,
            price=Decimal("5000.00"),
        )
        self.record_order(
            customer=customer,
            delivered_at=tied_delivery,
            price=Decimal("5000.00"),
        )

        first = self.assignment_for(customer)
        second = self.assignment_for(customer)

        self.assertEqual(first, second)
        self.assertEqual(first.segment, CustomerSegment.HIGH_VALUE)
        self.assertEqual(first.features.recorded_purchase_count, 2)
        self.assertEqual(first.features.last_recorded_purchase_at, tied_delivery)
        self.assertEqual(first.features.recency_days, 0)
        self.assertEqual(first.features.trailing_365_day_spend_bdt, Decimal("10000.00"))
