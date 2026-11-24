from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.catalog.models import Product
from apps.expenses.models import Expense
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from apps.profit.services.period_profit import summarize_period_profit
from tests.factories import FactoryContext, create_store_graph


class PeriodProfitSummaryTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="profit-period-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="profit-period-b"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Period Profit Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_a.store,
            name="Period Profit Product B",
            selling_price=Decimal("80.00"),
            unit_cost=Decimal("30.00"),
        )
        self.foreign_product = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Period Profit Product",
            selling_price=Decimal("500.00"),
            unit_cost=Decimal("100.00"),
        )

    def create_delivery(
        self,
        *,
        store,
        product,
        quantity,
        price,
        cost,
        discount,
        delivery_cost,
        occurred_at,
    ):
        order = SalesOrder.objects.create(
            store=store,
            status=SalesOrder.Status.DELIVERED,
            order_discount=discount,
            seller_delivery_cost=delivery_cost,
            delivered_at=occurred_at,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=quantity,
            selling_price_snapshot=price,
            unit_cost_snapshot=cost,
            discount_allocation=discount,
        )
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=store.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=occurred_at)
        return order

    def create_status_event(self, *, order, to_status, occurred_at):
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.DELIVERED,
            to_status=to_status,
            initiated_by=order.store.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=occurred_at)
        return event

    def summarize(self, start_date, end_date):
        return summarize_period_profit(
            store=self.graph_a.store,
            start_date=start_date,
            end_date=end_date,
        )

    def test_period_totals_reconcile_to_delivery_rows_and_same_store_expenses(self):
        first_order = self.create_delivery(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            cost=Decimal("40.00"),
            discount=Decimal("10.00"),
            delivery_cost=Decimal("15.00"),
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )
        second_order = self.create_delivery(
            store=self.graph_a.store,
            product=self.product_b,
            quantity=1,
            price=Decimal("80.00"),
            cost=Decimal("30.00"),
            discount=Decimal("0.00"),
            delivery_cost=Decimal("0.00"),
            occurred_at=datetime(2026, 1, 12, 9, 0, tzinfo=self.tz),
        )
        self.create_delivery(
            store=self.graph_b.store,
            product=self.foreign_product,
            quantity=1,
            price=Decimal("500.00"),
            cost=Decimal("100.00"),
            discount=Decimal("0.00"),
            delivery_cost=Decimal("0.00"),
            occurred_at=datetime(2026, 1, 12, 9, 0, tzinfo=self.tz),
        )
        Expense.objects.create(
            store=self.graph_a.store,
            recorded_by=self.graph_a.owner,
            description="Synthetic packaging",
            category="Packaging",
            amount=Decimal("12.00"),
            incurred_on=date(2026, 1, 15),
        )
        Expense.objects.create(
            store=self.graph_a.store,
            recorded_by=self.graph_a.owner,
            description="Synthetic advertising",
            category="Advertising",
            amount=Decimal("8.00"),
            incurred_on=date(2026, 1, 20),
        )
        Expense.objects.create(
            store=self.graph_b.store,
            recorded_by=self.graph_b.owner,
            description="Foreign synthetic advertising",
            category="Advertising",
            amount=Decimal("999.00"),
            incurred_on=date(2026, 1, 20),
        )

        summary = self.summarize(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(summary.net_revenue, Decimal("270.00"))
        self.assertEqual(summary.product_cost, Decimal("110.00"))
        self.assertEqual(summary.seller_delivery_cost, Decimal("15.00"))
        self.assertEqual(summary.recorded_operating_cost, Decimal("20.00"))
        self.assertEqual(summary.estimated_operational_profit, Decimal("125.00"))
        self.assertEqual(summary.estimated_profit_margin_percent, Decimal("46.30"))
        self.assertEqual(summary.completeness_status, "complete")
        self.assertEqual(len(summary.order_contributions), 2)
        self.assertEqual(len(summary.expense_contributions), 2)
        contributions = tuple(
            row.contribution for row in summary.order_contributions
        )
        self.assertEqual(
            summary.net_revenue,
            sum(
                (row.net_revenue_contribution for row in contributions),
                Decimal("0.00"),
            ),
        )
        self.assertEqual(
            summary.product_cost,
            sum(
                (row.product_cost_contribution for row in contributions),
                Decimal("0.00"),
            ),
        )
        self.assertEqual(
            summary.seller_delivery_cost,
            sum(
                (row.seller_delivery_cost_contribution for row in contributions),
                Decimal("0.00"),
            ),
        )
        self.assertEqual(
            summary.recorded_operating_cost,
            sum(
                (row.amount for row in summary.expense_contributions),
                Decimal("0.00"),
            ),
        )
        by_order = {
            row.contribution.order_id: row.contribution for row in summary.order_contributions
        }
        self.assertEqual(
            by_order[first_order.pk].estimated_contribution_before_operating_expenses,
            Decimal("95.00"),
        )
        self.assertEqual(
            by_order[second_order.pk].estimated_contribution_before_operating_expenses,
            Decimal("50.00"),
        )

    def test_first_later_terminal_event_reverses_once_in_its_own_period(self):
        order = self.create_delivery(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            cost=Decimal("40.00"),
            discount=Decimal("10.00"),
            delivery_cost=Decimal("15.00"),
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )
        self.create_status_event(
            order=order,
            to_status=SalesOrder.Status.RETURNED,
            occurred_at=datetime(2026, 2, 5, 9, 0, tzinfo=self.tz),
        )
        self.create_status_event(
            order=order,
            to_status=SalesOrder.Status.REFUNDED,
            occurred_at=datetime(2026, 2, 8, 9, 0, tzinfo=self.tz),
        )

        january = self.summarize(date(2026, 1, 1), date(2026, 1, 31))
        february = self.summarize(date(2026, 2, 1), date(2026, 2, 28))

        self.assertEqual(january.estimated_operational_profit, Decimal("95.00"))
        self.assertEqual(february.net_revenue, Decimal("-190.00"))
        self.assertEqual(february.product_cost, Decimal("-80.00"))
        self.assertEqual(february.seller_delivery_cost, Decimal("0.00"))
        self.assertEqual(february.estimated_operational_profit, Decimal("-110.00"))
        self.assertEqual(len(february.order_contributions), 1)

    def test_missing_transaction_cost_suppresses_profit_but_keeps_revenue(self):
        self.create_delivery(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=1,
            price=Decimal("100.00"),
            cost=None,
            discount=Decimal("0.00"),
            delivery_cost=None,
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )

        summary = self.summarize(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(summary.net_revenue, Decimal("100.00"))
        self.assertIsNone(summary.product_cost)
        self.assertIsNone(summary.seller_delivery_cost)
        self.assertIsNone(summary.estimated_operational_profit)
        self.assertIsNone(summary.estimated_profit_margin_percent)
        self.assertEqual(
            summary.completeness_status,
            "unavailable_missing_product_and_delivery_cost",
        )
