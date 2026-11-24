from datetime import datetime, timezone
from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from apps.segmentation.features import (
    CustomerFeatureError,
    calculate_customer_behavior_features,
)
from tests.factories import FactoryContext, create_store_graph


class CustomerBehaviorFeatureTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="segment-features"))
        self.customer = Customer.objects.create(
            store=self.graph.store, display_name="Synthetic Segment Buyer"
        )
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Synthetic Segment Product",
            selling_price=Decimal("500.00"),
            unit_cost=Decimal("100.00"),
        )
        self.as_of = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)

    def record_order(
        self,
        *,
        customer=None,
        status=SalesOrder.Status.DELIVERED,
        delivered_at,
        quantity=1,
        price=Decimal("100.00"),
        discount=Decimal("0.00"),
    ):
        order = SalesOrder.objects.create(
            store=self.graph.store,
            customer=customer or self.customer,
            status=status,
            delivered_at=delivered_at,
            order_discount=discount,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Synthetic Segment Product",
            quantity=quantity,
            selling_price_snapshot=price,
            unit_cost_snapshot=Decimal("100.00"),
        )
        return order

    def test_features_match_hand_calculated_eligible_snapshot_orders(self):
        self.record_order(
            delivered_at=datetime(2025, 7, 1, 12, tzinfo=timezone.utc),
            price=Decimal("100.00"),
        )
        self.record_order(
            delivered_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
            price=Decimal("300.00"),
        )
        self.record_order(
            delivered_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
            status=SalesOrder.Status.RETURN_REQUESTED,
            price=Decimal("200.00"),
        )
        latest = self.record_order(
            delivered_at=datetime(2026, 6, 30, 12, tzinfo=timezone.utc),
            quantity=2,
            price=Decimal("500.00"),
            discount=Decimal("100.00"),
        )
        self.record_order(
            delivered_at=datetime(2026, 6, 20, 12, tzinfo=timezone.utc),
            status=SalesOrder.Status.RETURNED,
            price=Decimal("999.00"),
        )
        self.record_order(
            delivered_at=datetime(2026, 7, 2, 12, tzinfo=timezone.utc),
            price=Decimal("999.00"),
        )
        self.product.selling_price = Decimal("9999.00")
        self.product.save()

        features = calculate_customer_behavior_features(
            store=self.graph.store, customer=self.customer, as_of=self.as_of
        )

        self.assertEqual(features.customer_id, self.customer.pk)
        self.assertEqual(features.segment_rule_version, "segment-v1")
        self.assertEqual(features.store_timezone, "Asia/Dhaka")
        self.assertEqual(features.recorded_purchase_count, 4)
        self.assertEqual(features.last_recorded_purchase_at, latest.delivered_at)
        self.assertEqual(features.recency_days, 1)
        self.assertEqual(features.trailing_365_day_spend_bdt, Decimal("1400.00"))

    def test_local_store_calendar_controls_recency_and_trailing_boundary(self):
        local_same_day_delivery = datetime(2026, 6, 30, 18, 30, tzinfo=timezone.utc)
        self.record_order(
            delivered_at=local_same_day_delivery,
            price=Decimal("250.00"),
        )

        features = calculate_customer_behavior_features(
            store=self.graph.store,
            customer=self.customer,
            as_of=datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(features.recency_days, 0)
        self.assertEqual(features.trailing_365_day_spend_bdt, Decimal("250.00"))

    def test_customer_without_eligible_orders_has_only_non_sensitive_empty_features(self):
        features = calculate_customer_behavior_features(
            store=self.graph.store, customer=self.customer, as_of=self.as_of
        )

        self.assertEqual(features.recorded_purchase_count, 0)
        self.assertIsNone(features.last_recorded_purchase_at)
        self.assertIsNone(features.recency_days)
        self.assertEqual(features.trailing_365_day_spend_bdt, Decimal("0.00"))
        self.assertEqual(
            set(features.__dataclass_fields__),
            {
                "customer_id",
                "as_of",
                "store_timezone",
                "segment_rule_version",
                "recorded_purchase_count",
                "last_recorded_purchase_at",
                "recency_days",
                "trailing_365_day_spend_bdt",
            },
        )

    def test_foreign_store_customer_and_naive_as_of_are_rejected(self):
        foreign_graph = create_store_graph(FactoryContext(namespace="segment-foreign"))
        foreign_customer = Customer.objects.create(
            store=foreign_graph.store, display_name="Other Synthetic Buyer"
        )

        with self.assertRaisesMessage(
            CustomerFeatureError, "Customer does not belong to the selected store."
        ):
            calculate_customer_behavior_features(
                store=self.graph.store, customer=foreign_customer, as_of=self.as_of
            )
        with self.assertRaisesMessage(
            CustomerFeatureError, "Use a timezone-aware as_of timestamp."
        ):
            calculate_customer_behavior_features(
                store=self.graph.store,
                customer=self.customer,
                as_of=datetime(2026, 7, 1, 12),
            )
