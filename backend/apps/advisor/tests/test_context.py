from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.advisor.context import AdvisorContextError, build_advisor_context
from apps.analytics.services.products import summarize_product_performance
from apps.analytics.services.sales import summarize_base_delivered_sales
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.customers.services import get_customer_purchase_history
from apps.expenses.models import Expense
from apps.inventory.models import StockUnit
from apps.inventory.services import summarize_stock_thresholds
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from apps.profit.services.period_profit import summarize_period_profit
from tests.factories import FactoryContext, create_store_graph


class AdvisorContextTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="advisor-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="advisor-b"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.start_date = date(2026, 1, 1)
        self.end_date = date(2026, 1, 31)

        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Advisor Tote",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.product_a,
            quantity_on_hand=2,
            low_stock_threshold=2,
        )
        self.customer_a = Customer.objects.create(
            store=self.graph_a.store,
            display_name="Synthetic Buyer",
            email="buyer@example.test",
            phone="01712345678",
        )
        self.order_a = SalesOrder.objects.create(
            store=self.graph_a.store,
            customer=self.customer_a,
            status=SalesOrder.Status.DELIVERED,
            order_discount=Decimal("10.00"),
            seller_delivery_cost=Decimal("15.00"),
            delivered_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )
        OrderItem.objects.create(
            order=self.order_a,
            product=self.product_a,
            product_name_snapshot=self.product_a.name,
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("40.00"),
            discount_allocation=Decimal("10.00"),
        )
        event = OrderStatusEvent.objects.create(
            order=self.order_a,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph_a.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz)
        )
        Expense.objects.create(
            store=self.graph_a.store,
            recorded_by=self.graph_a.owner,
            description="Synthetic packaging",
            category="Packaging",
            amount=Decimal("20.00"),
            incurred_on=date(2026, 1, 15),
        )

        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Product",
            selling_price=Decimal("999.00"),
            unit_cost=Decimal("100.00"),
        )
        self.customer_b = Customer.objects.create(
            store=self.graph_b.store,
            display_name="Foreign Buyer",
        )

    def test_context_values_exactly_match_existing_service_outputs(self):
        context = build_advisor_context(
            self.graph_a.owner,
            start_date=self.start_date,
            end_date=self.end_date,
            product_id=self.product_a.pk,
            customer_id=self.customer_a.pk,
        )
        profit = summarize_period_profit(
            store=self.graph_a.store,
            start_date=self.start_date,
            end_date=self.end_date,
        )
        sales = summarize_base_delivered_sales(
            store=self.graph_a.store,
            period_start=profit.period_start,
            period_end=profit.period_end,
        )
        products = summarize_product_performance(
            store=self.graph_a.store,
            period_start=profit.period_start,
            period_end=profit.period_end,
        )
        stock = summarize_stock_thresholds(store=self.graph_a.store)
        customer = get_customer_purchase_history(self.customer_a)

        self.assertEqual(context.store_id, self.graph_a.store.pk)
        self.assertEqual(context.store_timezone, "Asia/Dhaka")
        self.assertEqual(context.sales.delivered_order_count, sales.delivered_order_count)
        self.assertEqual(context.sales.delivered_units, sales.delivered_units)
        self.assertEqual(
            context.sales.delivered_net_sales_before_reversals,
            sales.delivered_net_sales_before_reversals,
        )
        self.assertEqual(context.profit.net_revenue, profit.net_revenue)
        self.assertEqual(
            context.profit.estimated_operational_profit,
            profit.estimated_operational_profit,
        )
        self.assertEqual(context.profit.completeness_status, profit.completeness_status)
        self.assertEqual(context.stock, stock)
        expected_product = products.products[0]
        self.assertEqual(context.product.product_id, expected_product.product_id)
        self.assertEqual(context.product.delivered_units, expected_product.delivered_units)
        self.assertEqual(
            context.product.delivered_gross_sales,
            expected_product.delivered_gross_sales,
        )
        self.assertEqual(context.customer.customer_id, self.customer_a.pk)
        self.assertEqual(context.customer.purchase_count, customer.purchase_count)
        self.assertEqual(context.customer.last_purchase_at, customer.last_purchase_at)
        self.assertEqual(context.customer.total_spend, customer.total_spend)

    def test_customer_context_excludes_display_name_and_contact_values(self):
        context = build_advisor_context(
            self.graph_a.staff,
            start_date=self.start_date,
            end_date=self.end_date,
            customer_id=self.customer_a.pk,
        )

        fields = context.customer.__dataclass_fields__
        self.assertNotIn("display_name", fields)
        self.assertNotIn("email", fields)
        self.assertNotIn("phone", fields)
        self.assertNotIn(self.customer_a.display_name, str(context.customer))
        self.assertNotIn(self.customer_a.email, str(context.customer))
        self.assertNotIn(self.customer_a.phone, str(context.customer))

    def test_foreign_optional_evidence_is_rejected_without_disclosure(self):
        for kwargs in (
            {"product_id": self.product_b.pk},
            {"customer_id": self.customer_b.pk},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(AdvisorContextError, "No authorized"):
                    build_advisor_context(
                        self.graph_a.owner,
                        start_date=self.start_date,
                        end_date=self.end_date,
                        **kwargs,
                    )
