from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class ProductPerformanceApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="performance-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="performance-api-b"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Performance API Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_a_second = Product.objects.create(
            store=self.graph_a.store,
            name="Performance API Product A Second",
            selling_price=Decimal("50.00"),
            unit_cost=Decimal("20.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Performance API Product B",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("80.00"),
        )
        self.url = reverse("product-performance")

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def create_delivered_order(self, *, store, product, quantity, price, delivered_at):
        order = SalesOrder.objects.create(
            store=store,
            status=SalesOrder.Status.DELIVERED,
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
            initiated_by=store.owner,
        )
        OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivered_at)

    def period_url(self, start, end):
        return f"{self.url}?{urlencode({'period_start': start.isoformat(), 'period_end': end.isoformat()})}"

    def test_product_breakdown_is_store_scoped_and_matches_order_line_facts(self):
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            delivered_at=datetime(2026, 1, 10, tzinfo=self.tz),
        )
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a_second,
            quantity=3,
            price=Decimal("50.00"),
            delivered_at=datetime(2026, 1, 15, tzinfo=self.tz),
        )
        self.create_delivered_order(
            store=self.graph_b.store,
            product=self.product_b,
            quantity=1,
            price=Decimal("200.00"),
            delivered_at=datetime(2026, 1, 12, tzinfo=self.tz),
        )
        self.authenticate(self.graph_a.staff)

        response = self.client.get(
            self.period_url(
                datetime(2026, 1, 1, tzinfo=self.tz),
                datetime(2026, 2, 1, tzinfo=self.tz),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result_state"], "data_present")
        self.assertEqual(response.data["data_completeness_status"], "unknown")
        self.assertEqual(response.data["return_adjustment_status"], "decision_required")
        by_product = {row["product_id"]: row for row in response.data["products"]}
        self.assertEqual(by_product[str(self.product_a.pk)]["delivered_units"], 2)
        self.assertEqual(
            by_product[str(self.product_a.pk)]["delivered_gross_sales"], "200.00"
        )
        self.assertEqual(by_product[str(self.product_a_second.pk)]["delivered_units"], 3)
        self.assertEqual(
            by_product[str(self.product_a_second.pk)]["delivered_gross_sales"],
            "150.00",
        )
        self.assertNotIn(str(self.product_b.pk), str(response.data))

    def test_empty_and_invalid_requests_fail_closed(self):
        start = datetime(2026, 1, 1, tzinfo=self.tz)
        end = datetime(2026, 2, 1, tzinfo=self.tz)
        unauthenticated = self.client.get(self.period_url(start, end))
        self.assertEqual(unauthenticated.status_code, 401)

        self.authenticate(self.graph_a.owner)
        empty_response = self.client.get(
            self.period_url(
                datetime(2026, 4, 1, tzinfo=self.tz),
                datetime(2026, 5, 1, tzinfo=self.tz),
            )
        )
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(
            empty_response.data["result_state"], "no_eligible_events_coverage_unknown"
        )
        self.assertEqual(empty_response.data["products"], [])

        invalid_response = self.client.get(
            f"{self.url}?period_start={start.isoformat()}&period_end={end.isoformat()}&store_id={self.graph_b.store.pk}"
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(invalid_response.data["error"]["code"], "validation_error")
        self.assertIn("store_id", invalid_response.data["error"]["details"])

    def test_period_start_is_inclusive_and_end_is_exclusive(self):
        period_start = datetime(2026, 1, 10, 0, 0, tzinfo=self.tz)
        period_end = datetime(2026, 1, 11, 0, 0, tzinfo=self.tz)
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            delivered_at=period_start,
        )
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=5,
            price=Decimal("100.00"),
            delivered_at=period_end,
        )
        self.authenticate(self.graph_a.owner)

        response = self.client.get(self.period_url(period_start, period_end))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result_state"], "data_present")
        self.assertEqual(
            response.data["products"],
            [
                {
                    "product_id": str(self.product_a.pk),
                    "delivered_units": 2,
                    "delivered_gross_sales": "200.00",
                }
            ],
        )
