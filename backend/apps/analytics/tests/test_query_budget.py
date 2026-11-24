"""Query-budget regression coverage for the authenticated analytics API."""
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class AnalyticsQueryBudgetTests(APITestCase):
    """Keep the documented request path bounded without asserting wall-clock time."""

    def test_product_performance_request_uses_at_most_six_queries(self):
        graph = create_store_graph(FactoryContext(namespace="analytics-budget"))
        product = Product.objects.create(
            store=graph.store,
            name="Analytics Budget Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        delivered_at = datetime(2026, 1, 10, 10, 0, tzinfo=ZoneInfo("Asia/Dhaka"))
        order = SalesOrder.objects.create(
            store=graph.store,
            status=SalesOrder.Status.DELIVERED,
            delivered_at=delivered_at,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=product.unit_cost,
        )
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=graph.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivered_at)
        token = Token.objects.create(user=graph.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        period_parameters = {
            "period_start": datetime(2026, 1, 1, tzinfo=delivered_at.tzinfo).isoformat(),
            "period_end": datetime(2026, 2, 1, tzinfo=delivered_at.tzinfo).isoformat(),
        }
        url = f"{reverse('product-performance')}?{urlencode(period_parameters)}"

        with CaptureQueriesContext(connection) as captured_queries:
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured_queries), 6)
