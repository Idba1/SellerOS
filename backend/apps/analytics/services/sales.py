"""Deterministic base-delivered sales aggregation from immutable order evidence."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Store
from apps.orders.models import OrderStatusEvent, SalesOrder


ZERO_MONEY = Decimal("0.00")


class SalesAggregationError(ValueError):
    """Raised when the requested evidence cannot form a trustworthy base summary."""


@dataclass(frozen=True)
class ProductSalesSummary:
    """Snapshot-based delivered gross sales for one product identity."""

    product_id: object
    delivered_units: int
    delivered_gross_sales: Decimal


@dataclass(frozen=True)
class SalesSummary:
    """Base-delivered totals without return adjustment, COGS, or profit arithmetic."""

    period_start: datetime
    period_end: datetime
    delivered_order_count: int
    delivered_units: int
    delivered_gross_sales: Decimal
    delivered_order_discounts: Decimal
    delivered_net_sales_before_reversals: Decimal
    products: tuple[ProductSalesSummary, ...]
    data_completeness_status: str = "unknown"
    return_adjustment_status: str = "decision_required"


def summarize_base_delivered_sales(*, store: Store, period_start: datetime, period_end: datetime) -> SalesSummary:
    """Summarize original delivery events in an explicit aware ``[start, end)`` interval.

    The caller must resolve the authorized store and convert any user-selected
    local dates to aware timestamps before calling this internal service. This
    avoids choosing the still-unresolved public range and bucketing contract.
    """

    _validate_period(store=store, period_start=period_start, period_end=period_end)

    delivered_events = list(
        OrderStatusEvent.objects.filter(
            order__store=store,
            to_status=SalesOrder.Status.DELIVERED,
            occurred_at__gte=period_start,
            occurred_at__lt=period_end,
        )
        .select_related("order")
        .prefetch_related("order__items")
        .order_by("occurred_at", "id")
    )
    _reject_duplicate_delivery_evidence(delivered_events)

    delivered_order_count = len(delivered_events)
    delivered_units = 0
    delivered_gross_sales = ZERO_MONEY
    delivered_order_discounts = ZERO_MONEY
    product_totals: dict[object, list[Decimal | int]] = defaultdict(
        lambda: [0, ZERO_MONEY]
    )

    for event in delivered_events:
        order = event.order
        delivered_order_discounts += order.order_discount
        for item in order.items.all():
            line_gross = item.quantity * item.selling_price_snapshot
            delivered_units += item.quantity
            delivered_gross_sales += line_gross
            product_totals[item.product_id][0] += item.quantity
            product_totals[item.product_id][1] += line_gross

    products = tuple(
        ProductSalesSummary(
            product_id=product_id,
            delivered_units=values[0],
            delivered_gross_sales=values[1],
        )
        for product_id, values in sorted(product_totals.items(), key=lambda item: str(item[0]))
    )
    return SalesSummary(
        period_start=period_start,
        period_end=period_end,
        delivered_order_count=delivered_order_count,
        delivered_units=delivered_units,
        delivered_gross_sales=delivered_gross_sales,
        delivered_order_discounts=delivered_order_discounts,
        delivered_net_sales_before_reversals=(
            delivered_gross_sales - delivered_order_discounts
        ),
        products=products,
    )


def _validate_period(*, store, period_start, period_end):
    if not isinstance(store, Store):
        raise SalesAggregationError("A server-resolved store is required.")
    if not isinstance(period_start, datetime) or not isinstance(period_end, datetime):
        raise SalesAggregationError("Use datetime period boundaries.")
    if timezone.is_naive(period_start) or timezone.is_naive(period_end):
        raise SalesAggregationError("Use timezone-aware period boundaries.")
    if period_end <= period_start:
        raise SalesAggregationError("Period end must be after period start.")


def _reject_duplicate_delivery_evidence(delivered_events):
    order_ids = [event.order_id for event in delivered_events]
    if not order_ids:
        return
    duplicate_exists = (
        OrderStatusEvent.objects.filter(
            order_id__in=order_ids,
            to_status=SalesOrder.Status.DELIVERED,
        )
        .values("order_id")
        .annotate(event_count=Count("id"))
        .filter(event_count__gt=1)
        .exists()
    )
    if duplicate_exists:
        raise SalesAggregationError(
            "Duplicate delivery evidence prevents a trustworthy sales summary."
        )
