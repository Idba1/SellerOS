from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product
from apps.orders.models import OrderItem, SalesOrder
from apps.profit.services.order_profit import (
    OrderProfitCalculationError,
    OrderProfitContributionType,
    calculate_order_profit_contribution,
)
from tests.factories import FactoryContext, create_store_graph


class OrderProfitContributionTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="profit-order"))
        self.product_a = Product.objects.create(
            store=self.graph.store,
            name="Profit Snapshot Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph.store,
            name="Profit Snapshot Product B",
            selling_price=Decimal("80.00"),
            unit_cost=Decimal("30.00"),
        )

    def create_order(
        self,
        *,
        delivery_cost=Decimal("15.00"),
        discount=Decimal("10.00"),
    ):
        order = SalesOrder.objects.create(
            store=self.graph.store,
            status=SalesOrder.Status.DELIVERED,
            order_discount=discount,
            seller_delivery_cost=delivery_cost,
        )
        first = OrderItem.objects.create(
            order=order,
            product=self.product_a,
            product_name_snapshot="Historical Product A",
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("40.00"),
            discount_allocation=Decimal("10.00"),
        )
        second = OrderItem.objects.create(
            order=order,
            product=self.product_b,
            product_name_snapshot="Historical Product B",
            quantity=1,
            selling_price_snapshot=Decimal("80.00"),
            unit_cost_snapshot=Decimal("30.00"),
            discount_allocation=Decimal("0.00"),
        )
        return order, first, second

    def test_delivery_contribution_matches_the_hand_calculation_and_snapshots(self):
        order, first, second = self.create_order()
        self.product_a.selling_price = Decimal("999.00")
        self.product_a.unit_cost = Decimal("888.00")
        self.product_a.save()

        contribution = calculate_order_profit_contribution(order=order)

        self.assertEqual(
            contribution.contribution_type,
            OrderProfitContributionType.DELIVERY,
        )
        self.assertEqual(contribution.gross_revenue, Decimal("280.00"))
        self.assertEqual(contribution.discount_total, Decimal("10.00"))
        self.assertEqual(contribution.net_revenue_contribution, Decimal("270.00"))
        self.assertEqual(contribution.product_cost_contribution, Decimal("110.00"))
        self.assertEqual(
            contribution.seller_delivery_cost_contribution,
            Decimal("15.00"),
        )
        self.assertEqual(
            contribution.estimated_contribution_before_operating_expenses,
            Decimal("145.00"),
        )
        self.assertEqual(contribution.estimated_margin_percent, Decimal("53.70"))
        self.assertEqual(contribution.completeness_status, "complete")
        by_item = {item.order_item_id: item for item in contribution.items}
        self.assertEqual(
            by_item[first.pk].net_revenue_contribution,
            Decimal("190.00"),
        )
        self.assertEqual(
            by_item[first.pk].product_cost_contribution,
            Decimal("80.00"),
        )
        self.assertEqual(
            by_item[second.pk].net_revenue_contribution,
            Decimal("80.00"),
        )

    def test_missing_product_or_delivery_cost_suppresses_profit_and_margin(self):
        order, first, _ = self.create_order()
        first.unit_cost_snapshot = None
        first.save(update_fields={"unit_cost_snapshot"})

        missing_product_cost = calculate_order_profit_contribution(order=order)

        self.assertIsNone(missing_product_cost.product_cost_contribution)
        self.assertIsNone(
            missing_product_cost.estimated_contribution_before_operating_expenses
        )
        self.assertIsNone(missing_product_cost.estimated_margin_percent)
        self.assertEqual(
            missing_product_cost.completeness_status,
            "unavailable_missing_product_cost",
        )

        order_with_missing_delivery, _, _ = self.create_order(delivery_cost=None)
        missing_delivery_cost = calculate_order_profit_contribution(
            order=order_with_missing_delivery
        )

        self.assertEqual(
            missing_delivery_cost.product_cost_contribution,
            Decimal("110.00"),
        )
        self.assertIsNone(missing_delivery_cost.seller_delivery_cost_contribution)
        self.assertIsNone(
            missing_delivery_cost.estimated_contribution_before_operating_expenses
        )
        self.assertEqual(
            missing_delivery_cost.completeness_status,
            "unavailable_missing_delivery_cost",
        )

    def test_reversal_negates_revenue_and_cogs_without_reversing_delivery_cost(self):
        order, _, _ = self.create_order()

        contribution = calculate_order_profit_contribution(
            order=order,
            contribution_type=OrderProfitContributionType.REVERSAL,
        )

        self.assertEqual(contribution.net_revenue_contribution, Decimal("-270.00"))
        self.assertEqual(contribution.product_cost_contribution, Decimal("-110.00"))
        self.assertEqual(
            contribution.seller_delivery_cost_contribution,
            Decimal("0.00"),
        )
        self.assertEqual(
            contribution.estimated_contribution_before_operating_expenses,
            Decimal("-160.00"),
        )
        self.assertIsNone(contribution.estimated_margin_percent)
        self.assertEqual(contribution.completeness_status, "complete")

    def test_inconsistent_discount_allocation_fails_closed(self):
        order, first, _ = self.create_order()
        first.discount_allocation = Decimal("9.99")
        first.save(update_fields={"discount_allocation"})

        with self.assertRaisesMessage(
            OrderProfitCalculationError,
            "Order-item discount allocations must equal the order discount.",
        ):
            calculate_order_profit_contribution(order=order)
