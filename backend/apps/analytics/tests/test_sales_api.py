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


class SalesSummaryApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="sales-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="sales-api-b"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Sales API Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Sales API Product B",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("80.00"),
        )
        self.url = reverse("sales-summary")

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def create_delivered_order(
        self,
        *,
        store,
        product,
        quantity,
        price,
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

    def summary_url(self, start, end):
        return f"{self.url}?{urlencode({'period_start': start.isoformat(), 'period_end': end.isoformat()})}"

    def test_summary_uses_same_store_delivery_events_and_stable_response_shape(self):
        self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            delivered_at=datetime(2026, 1, 10, 10, 0, tzinfo=self.tz),
            discount=Decimal("10.00"),
            status=SalesOrder.Status.RETURNED,
        )
        self.create_delivered_order(
            store=self.graph_b.store,
            product=self.product_b,
            quantity=1,
            price=Decimal("200.00"),
            delivered_at=datetime(2026, 1, 11, 10, 0, tzinfo=self.tz),
        )
        self.authenticate(self.graph_a.staff)

        response = self.client.get(
            self.summary_url(
                datetime(2026, 1, 1, tzinfo=self.tz),
                datetime(2026, 2, 1, tzinfo=self.tz),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["store_timezone"], "Asia/Dhaka")
        self.assertEqual(response.data["result_state"], "data_present")
        self.assertEqual(response.data["totals"]["delivered_order_count"], 1)
        self.assertEqual(response.data["totals"]["delivered_units"], 2)
        self.assertEqual(response.data["totals"]["delivered_gross_sales"], "200.00")
        self.assertEqual(response.data["totals"]["delivered_order_discounts"], "10.00")
        self.assertEqual(
            response.data["totals"]["delivered_net_sales_before_reversals"],
            "190.00",
        )
        self.assertEqual(response.data["totals"]["data_completeness_status"], "unknown")
        self.assertEqual(
            response.data["totals"]["return_adjustment_status"],
            "decision_required",
        )
        self.assertEqual(response.data["products"][0]["product_id"], str(self.product_a.pk))
        self.assertNotIn(str(self.product_b.pk), str(response.data))

    def test_empty_result_does_not_claim_complete_coverage(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(
            self.summary_url(
                datetime(2026, 4, 1, tzinfo=self.tz),
                datetime(2026, 5, 1, tzinfo=self.tz),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["result_state"], "no_eligible_events_coverage_unknown"
        )
        self.assertEqual(response.data["totals"]["delivered_order_count"], 0)
        self.assertEqual(response.data["totals"]["delivered_gross_sales"], "0.00")
        self.assertEqual(response.data["products"], [])

    def test_authentication_and_period_validation_fail_closed(self):
        start = datetime(2026, 1, 1, tzinfo=self.tz)
        end = datetime(2026, 2, 1, tzinfo=self.tz)
        unauthenticated = self.client.get(self.summary_url(start, end))
        self.assertEqual(unauthenticated.status_code, 401)

        self.authenticate(self.graph_a.owner)
        cases = (
            (f"{self.url}?period_end={end.isoformat()}", "period_start"),
            (
                f"{self.url}?period_start=2026-01-01T00:00:00&period_end={end.isoformat()}",
                "period_start",
            ),
            (self.summary_url(end, start), "non_field_errors"),
            (
                f"{self.summary_url(start, end)}&store_id={self.graph_b.store.pk}",
                "store_id",
            ),
        )
        for url, field in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

    def test_duplicate_delivery_evidence_returns_a_stable_validation_error(self):
        delivered_at = datetime(2026, 1, 10, 10, 0, tzinfo=self.tz)
        order = self.create_delivered_order(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=1,
            price=Decimal("100.00"),
            delivered_at=delivered_at,
        )
        duplicate_event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.RETURN_REQUESTED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph_a.owner,
        )
        OrderStatusEvent.objects.filter(pk=duplicate_event.pk).update(
            occurred_at=datetime(2026, 1, 11, 10, 0, tzinfo=self.tz)
        )
        self.authenticate(self.graph_a.owner)

        response = self.client.get(
            self.summary_url(
                datetime(2026, 1, 1, tzinfo=self.tz),
                datetime(2026, 2, 1, tzinfo=self.tz),
            )
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertEqual(
            response.data["error"]["details"]["non_field_errors"],
            ["Duplicate delivery evidence prevents a trustworthy sales summary."],
        )
