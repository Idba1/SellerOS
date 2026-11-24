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
from apps.profit.tests.profit_cases import (
    PROFIT_CASE_SET_VERSION,
    PROFIT_REGRESSION_CASES,
    ProfitRegressionCase,
)
from tests.factories import FactoryContext, create_store_graph


class ProfitRegressionCaseTests(APITestCase):
    """Verify the public API against versioned, independently hand-calculated data."""

    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="profit-cases"))
        self.tz = ZoneInfo("Asia/Dhaka")
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Profit Regression Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        token = Token.objects.create(user=self.graph.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = reverse("profit-summary")

    def test_case_set_version_and_hand_calculated_totals_match_api_output(self):
        self.assertEqual(PROFIT_CASE_SET_VERSION, "profit-regression-v1")
        for case in PROFIT_REGRESSION_CASES:
            with self.subTest(case_id=case.case_id):
                self._clear_case_records()
                self._load_case(case)

                response = self.client.get(
                    f"{self.url}?{urlencode({'start_date': '2026-01-01', 'end_date': '2026-01-31'})}"
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["totals"], case.expected_totals)
                self.assertEqual(
                    response.data["completeness"]["status"],
                    case.expected_completeness_status,
                )
                self.assertEqual(
                    response.data["calculation_basis"]["formula"],
                    "net revenue - product cost - seller delivery cost "
                    "- recorded operating cost",
                )

    def _load_case(self, case: ProfitRegressionCase) -> None:
        if case.quantity is not None:
            delivery_at = datetime(2026, 1, 10, 9, 0, tzinfo=self.tz)
            order = SalesOrder.objects.create(
                store=self.graph.store,
                status=SalesOrder.Status.DELIVERED,
                order_discount=Decimal(case.discount),
                seller_delivery_cost=_decimal_or_none(case.seller_delivery_cost),
                delivered_at=delivery_at,
            )
            OrderItem.objects.create(
                order=order,
                product=self.product,
                product_name_snapshot=self.product.name,
                quantity=case.quantity,
                selling_price_snapshot=Decimal(case.selling_price),
                unit_cost_snapshot=_decimal_or_none(case.unit_cost),
                discount_allocation=Decimal(case.discount),
            )
            event = OrderStatusEvent.objects.create(
                order=order,
                from_status=SalesOrder.Status.SHIPPED,
                to_status=SalesOrder.Status.DELIVERED,
                initiated_by=self.graph.owner,
            )
            OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=delivery_at)
        Expense.objects.create(
            store=self.graph.store,
            recorded_by=self.graph.owner,
            description=f"Synthetic {case.case_id} expense",
            category="Regression",
            amount=Decimal(case.recorded_operating_cost),
            incurred_on=date(2026, 1, 15),
        )

    @staticmethod
    def _clear_case_records() -> None:
        OrderStatusEvent.objects.all().delete()
        OrderItem.objects.all().delete()
        SalesOrder.objects.all().delete()
        Expense.objects.all().delete()


def _decimal_or_none(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)
