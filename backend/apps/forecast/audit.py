"""Reproducible audit of store-scoped delivery history for forecast gating."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from apps.accounts.models import Store
from apps.orders.models import OrderStatusEvent, SalesOrder


class ForecastDataAuditError(ValueError):
    """Safe error for an audit invoked without a server-resolved store."""


@dataclass(frozen=True)
class DateGap:
    start_date: date
    end_date: date


@dataclass(frozen=True)
class ForecastDataAudit:
    """Observed delivery-history quality facts, not a readiness prediction."""

    store_id: UUID
    store_timezone: str
    source: str
    raw_delivery_event_count: int
    unique_delivery_order_count: int
    valid_delivery_event_count: int
    duplicate_delivery_order_count: int
    date_span_start: date | None
    date_span_end: date | None
    calendar_day_count: int
    days_with_valid_deliveries: int
    gap_day_count: int
    gap_ranges: tuple[DateGap, ...]
    products_with_valid_delivery_count: int
    valid_delivery_orders_without_items_count: int
    return_requested_order_count: int
    returned_or_refunded_order_count: int
    observed_granularity: str
    forecast_training_permitted: bool
    limitation_codes: tuple[str, ...]


def audit_store_delivery_history(*, store: Store) -> ForecastDataAudit:
    """Audit immutable original delivery evidence without training a model.

    Callers resolve store authorization before calling this service. Duplicate
    delivery events are reported and excluded from the usable date series rather
    than silently selecting one. A current returned/refunded state is reported
    as a limitation; this task does not decide a return-adjusted demand series.
    """

    if not isinstance(store, Store):
        raise ForecastDataAuditError("A server-resolved store is required.")

    events = list(
        OrderStatusEvent.objects.filter(
            order__store=store,
            to_status=SalesOrder.Status.DELIVERED,
        )
        .select_related("order")
        .prefetch_related("order__items")
        .order_by("occurred_at", "id")
    )
    events_by_order: dict[UUID, list[OrderStatusEvent]] = defaultdict(list)
    for event in events:
        events_by_order[event.order_id].append(event)

    duplicate_order_ids = {
        order_id for order_id, order_events in events_by_order.items() if len(order_events) > 1
    }
    valid_events = tuple(event for event in events if event.order_id not in duplicate_order_ids)
    store_timezone = ZoneInfo(store.timezone)
    delivery_dates = tuple(
        event.occurred_at.astimezone(store_timezone).date() for event in valid_events
    )
    unique_delivery_dates = tuple(sorted(set(delivery_dates)))
    date_span_start = unique_delivery_dates[0] if unique_delivery_dates else None
    date_span_end = unique_delivery_dates[-1] if unique_delivery_dates else None
    gap_ranges = _find_gap_ranges(unique_delivery_dates)
    calendar_day_count = (
        0
        if date_span_start is None or date_span_end is None
        else (date_span_end - date_span_start).days + 1
    )
    products_with_delivery = {
        item.product_id for event in valid_events for item in event.order.items.all()
    }
    orders_without_items = sum(not event.order.items.all() for event in valid_events)
    valid_orders = tuple(event.order for event in valid_events)
    return_requested_count = sum(
        order.status == SalesOrder.Status.RETURN_REQUESTED for order in valid_orders
    )
    terminal_return_count = sum(
        order.status in {SalesOrder.Status.RETURNED, SalesOrder.Status.REFUNDED}
        for order in valid_orders
    )

    limitation_codes = _limitation_codes(
        valid_delivery_event_count=len(valid_events),
        duplicate_delivery_order_count=len(duplicate_order_ids),
        gap_ranges=gap_ranges,
        orders_without_items=orders_without_items,
        return_requested_count=return_requested_count,
        terminal_return_count=terminal_return_count,
    )
    return ForecastDataAudit(
        store_id=store.pk,
        store_timezone=store.timezone,
        source="original_delivered_status_events",
        raw_delivery_event_count=len(events),
        unique_delivery_order_count=len(events_by_order),
        valid_delivery_event_count=len(valid_events),
        duplicate_delivery_order_count=len(duplicate_order_ids),
        date_span_start=date_span_start,
        date_span_end=date_span_end,
        calendar_day_count=calendar_day_count,
        days_with_valid_deliveries=len(unique_delivery_dates),
        gap_day_count=sum(
            (gap.end_date - gap.start_date).days + 1 for gap in gap_ranges
        ),
        gap_ranges=gap_ranges,
        products_with_valid_delivery_count=len(products_with_delivery),
        valid_delivery_orders_without_items_count=orders_without_items,
        return_requested_order_count=return_requested_count,
        returned_or_refunded_order_count=terminal_return_count,
        observed_granularity="event_timestamp_with_store_local_daily_coverage_audit",
        forecast_training_permitted=False,
        limitation_codes=limitation_codes,
    )


def _find_gap_ranges(observed_dates: tuple[date, ...]) -> tuple[DateGap, ...]:
    gaps: list[DateGap] = []
    for previous, current in zip(observed_dates, observed_dates[1:]):
        gap_start = previous + timedelta(days=1)
        gap_end = current - timedelta(days=1)
        if gap_start <= gap_end:
            gaps.append(DateGap(start_date=gap_start, end_date=gap_end))
    return tuple(gaps)


def _limitation_codes(
    *,
    valid_delivery_event_count: int,
    duplicate_delivery_order_count: int,
    gap_ranges: tuple[DateGap, ...],
    orders_without_items: int,
    return_requested_count: int,
    terminal_return_count: int,
) -> tuple[str, ...]:
    limitations = [
        "history_coverage_unknown",
        "current_audit_does_not_authorize_forecast_training",
    ]
    if valid_delivery_event_count == 0:
        limitations.append("no_valid_delivery_events")
    if duplicate_delivery_order_count:
        limitations.append("duplicate_delivery_evidence")
    if gap_ranges:
        limitations.append("calendar_gaps_present")
    if orders_without_items:
        limitations.append("delivered_orders_without_items")
    if return_requested_count or terminal_return_count:
        limitations.append("return_treatment_not_approved_for_forecast_series")
    return tuple(limitations)
