from datetime import date, datetime, time, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.analytics.services.products import summarize_product_performance
from apps.analytics.services.sales import summarize_base_delivered_sales
from apps.catalog.models import Product
from apps.expenses.models import Expense
from apps.inventory.models import StockUnit
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from apps.profit.services.period_profit import summarize_period_profit
from tests.factories import FactoryContext, create_store_graph


class DashboardSummaryApiTests(APITestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="dashboard-api"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product = Product.objects.create(store=self.graph.store, name="Dashboard Product", selling_price=Decimal("100.00"), unit_cost=Decimal("40.00"))
        StockUnit.objects.create(store=self.graph.store, product=self.product, quantity_on_hand=2, low_stock_threshold=2)
        self.url = reverse("dashboard-summary")

    def test_composed_values_match_component_services(self):
        delivered_at = datetime(2026, 1, 10, 9, tzinfo=self.tz)
        order = SalesOrder.objects.create(store=self.graph.store, status=SalesOrder.Status.DELIVERED, order_discount=Decimal("10.00"), seller_delivery_cost=Decimal("15.00"))
        OrderItem.objects.create(order=order, product=self.product, product_name_snapshot=self.product.name, quantity=2, selling_price_snapshot=Decimal("100.00"), unit_cost_snapshot=Decimal("40.00"), discount_allocation=Decimal("10.00"))
        event = OrderStatusEvent.objects.create(order=order, from_status=SalesOrder.Status.SHIPPED, to_status=SalesOrder.Status.DELIVERED, initiated_by=self.graph.owner)
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivered_at)
        Expense.objects.create(store=self.graph.store, recorded_by=self.graph.owner, description="Dashboard expense", category="Packaging", amount=Decimal("20.00"), incurred_on=date(2026, 1, 15))
        token = Token.objects.create(user=self.graph.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(f"{self.url}?{urlencode({'start_date': '2026-01-01', 'end_date': '2026-01-31'})}")
        period_start = datetime.combine(date(2026, 1, 1), time.min, tzinfo=self.tz)
        period_end = datetime.combine(date(2026, 2, 1), time.min, tzinfo=self.tz)
        sales = summarize_base_delivered_sales(store=self.graph.store, period_start=period_start, period_end=period_end)
        products = summarize_product_performance(store=self.graph.store, period_start=period_start, period_end=period_end)
        profit = summarize_period_profit(store=self.graph.store, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sales"]["totals"]["delivered_net_sales_before_reversals"], f"{sales.delivered_net_sales_before_reversals:.2f}")
        self.assertEqual(response.data["products"]["products"][0]["delivered_gross_sales"], f"{products.products[0].delivered_gross_sales:.2f}")
        self.assertEqual(response.data["profit"]["estimated_operational_profit"], f"{profit.estimated_operational_profit:.2f}")
        self.assertEqual(response.data["inventory"]["low_stock_count"], 1)
