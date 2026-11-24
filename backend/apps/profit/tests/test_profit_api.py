from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.expenses.models import Expense
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class ProfitSummaryApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="profit-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="profit-api-b"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Profit API Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Profit API Product",
            selling_price=Decimal("500.00"),
            unit_cost=Decimal("100.00"),
        )
        self.url = reverse("profit-summary")

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def summary_url(self, start_date, end_date):
        return f"{self.url}?{urlencode({'start_date': start_date, 'end_date': end_date})}"

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
        event.refresh_from_db()
        return order, event

    def test_summary_returns_totals_basis_and_same_store_included_records(self):
        order, event = self.create_delivery(
            store=self.graph_a.store,
            product=self.product_a,
            quantity=2,
            price=Decimal("100.00"),
            cost=Decimal("40.00"),
            discount=Decimal("10.00"),
            delivery_cost=Decimal("15.00"),
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )
        self.create_delivery(
            store=self.graph_b.store,
            product=self.product_b,
            quantity=1,
            price=Decimal("500.00"),
            cost=Decimal("100.00"),
            discount=Decimal("0.00"),
            delivery_cost=Decimal("0.00"),
            occurred_at=datetime(2026, 1, 10, 9, 0, tzinfo=self.tz),
        )
        expense = Expense.objects.create(
            store=self.graph_a.store,
            recorded_by=self.graph_a.owner,
            description="Synthetic profit API expense",
            category="Packaging",
            amount=Decimal("20.00"),
            incurred_on=date(2026, 1, 15),
        )
        Expense.objects.create(
            store=self.graph_b.store,
            recorded_by=self.graph_b.owner,
            description="Foreign synthetic profit API expense",
            category="Packaging",
            amount=Decimal("999.00"),
            incurred_on=date(2026, 1, 15),
        )
        self.authenticate(self.graph_a.staff)

        response = self.client.get(self.summary_url("2026-01-01", "2026-01-31"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["store_timezone"], "Asia/Dhaka")
        self.assertEqual(response.data["period"]["start_date"], "2026-01-01")
        self.assertEqual(response.data["period"]["end_date"], "2026-01-31")
        self.assertEqual(
            response.data["totals"],
            {
                "net_revenue": "190.00",
                "product_cost": "80.00",
                "seller_delivery_cost": "15.00",
                "recorded_operating_cost": "20.00",
                "estimated_operational_profit": "75.00",
                "estimated_profit_margin_percent": "39.47",
            },
        )
        self.assertEqual(response.data["completeness"]["status"], "complete")
        self.assertTrue(response.data["completeness"]["profit_available"])
        self.assertIn(
            "Estimated operational profit is not a tax, cash-flow, or formal accounting statement.",
            response.data["completeness"]["warnings"],
        )
        self.assertEqual(
            response.data["calculation_basis"]["formula"],
            "net revenue - product cost - seller delivery cost - recorded operating cost",
        )
        self.assertEqual(
            response.data["included_records"]["order_events"],
            [
                {
                    "event_id": str(event.pk),
                    "occurred_at": event.occurred_at.isoformat(),
                    "order_id": str(order.pk),
                    "contribution_type": "delivery",
                    "net_revenue_contribution": "190.00",
                    "product_cost_contribution": "80.00",
                    "seller_delivery_cost_contribution": "15.00",
                    "estimated_contribution_before_operating_expenses": "95.00",
                    "completeness_status": "complete",
                }
            ],
        )
        self.assertEqual(
            response.data["included_records"]["expenses"],
            [
                {
                    "expense_id": str(expense.pk),
                    "incurred_on": "2026-01-15",
                    "amount": "20.00",
                }
            ],
        )
        self.assertNotIn(str(self.graph_b.store.pk), str(response.data))

    def test_incomplete_cost_exposes_warning_without_inventing_profit(self):
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
        self.authenticate(self.graph_a.owner)

        response = self.client.get(self.summary_url("2026-01-01", "2026-01-31"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["totals"]["net_revenue"], "100.00")
        self.assertIsNone(response.data["totals"]["product_cost"])
        self.assertIsNone(response.data["totals"]["seller_delivery_cost"])
        self.assertIsNone(response.data["totals"]["estimated_operational_profit"])
        self.assertFalse(response.data["completeness"]["profit_available"])
        self.assertEqual(
            response.data["completeness"]["status"],
            "unavailable_missing_product_and_delivery_cost",
        )
        self.assertEqual(len(response.data["completeness"]["warnings"]), 3)

    def test_authentication_and_query_validation_fail_closed(self):
        valid_url = self.summary_url("2026-01-01", "2026-01-31")
        unauthenticated = self.client.get(valid_url)
        self.assertEqual(unauthenticated.status_code, 401)

        self.authenticate(self.graph_a.owner)
        cases = (
            (f"{self.url}?end_date=2026-01-31", "start_date"),
            (
                self.summary_url("2026-01-31", "2026-01-01"),
                "non_field_errors",
            ),
            (
                f"{valid_url}&store_id={self.graph_b.store.pk}",
                "store_id",
            ),
            (
                f"{valid_url}&start_date=2026-01-01",
                "start_date",
            ),
        )
        for url, field in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])
