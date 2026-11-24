"""Store-period estimated-profit aggregation from order events and expenses."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from apps.accounts.models import Store
from apps.expenses.models import Expense
from apps.orders.models import OrderStatusEvent, SalesOrder

from .order_profit import (
    MONEY_QUANTUM,
    ZERO_MONEY,
    OrderProfitContribution,
    OrderProfitContributionType,
    calculate_order_profit_contribution,
)


PERCENTAGE_QUANTUM = Decimal("0.01")
TERMINAL_REVERSAL_STATUSES = {
    SalesOrder.Status.RETURNED,
    SalesOrder.Status.REFUNDED,
}


class PeriodProfitAggregationError(ValueError):
    """Raised when event history cannot safely support a period aggregate."""


@dataclass(frozen=True)
class ProfitEventContribution:
    """An eligible event and its reconciliable order contribution."""

    event_id: object
    occurred_at: datetime
    contribution: OrderProfitContribution


@dataclass(frozen=True)
class ExpenseContribution:
    """One recorded store-level operating cost in the selected business period."""

    expense_id: object
    amount: Decimal


@dataclass(frozen=True)
class PeriodProfitSummary:
    """Period totals before tax and other explicitly excluded accounting inputs."""

    store_id: object
    start_date: date
    end_date: date
    period_start: datetime
    period_end: datetime
    order_contributions: tuple[ProfitEventContribution, ...]
    expense_contributions: tuple[ExpenseContribution, ...]
    net_revenue: Decimal
    product_cost: Decimal | None
    seller_delivery_cost: Decimal | None
    recorded_operating_cost: Decimal
    estimated_operational_profit: Decimal | None
    estimated_profit_margin_percent: Decimal | None
    completeness_status: str


def summarize_period_profit(
    *,
    store: Store,
    start_date: date,
    end_date: date,
) -> PeriodProfitSummary:
    """Aggregate one store's whole-day profit period under the PROFIT-01 policy.

    Authorization is intentionally outside this pure deterministic service: the
    caller must resolve the permitted store server-side before invoking it.
    """

    period_start, period_end = _validate_and_build_period(
        store=store,
        start_date=start_date,
        end_date=end_date,
    )
    delivery_events = list(
        OrderStatusEvent.objects.filter(
            order__store=store,
            to_status=SalesOrder.Status.DELIVERED,
            occurred_at__gte=period_start,
            occurred_at__lt=period_end,
        )
        .select_related("order")
        .order_by("occurred_at", "id")
    )
    reversal_events = list(
        OrderStatusEvent.objects.filter(
            order__store=store,
            to_status__in=TERMINAL_REVERSAL_STATUSES,
            occurred_at__gte=period_start,
            occurred_at__lt=period_end,
        )
        .select_related("order")
        .order_by("occurred_at", "id")
    )
    event_history = _event_history_for({
        event.order_id for event in delivery_events + reversal_events
    })
    order_contributions = _order_contributions(
        delivery_events=delivery_events,
        reversal_events=reversal_events,
        event_history=event_history,
    )
    expense_contributions = tuple(
        ExpenseContribution(expense_id=expense.pk, amount=_money(expense.amount))
        for expense in Expense.objects.filter(
            store=store,
            incurred_on__gte=start_date,
            incurred_on__lte=end_date,
        ).order_by("incurred_on", "created_at", "id")
    )
    return _summarize(
        store=store,
        start_date=start_date,
        end_date=end_date,
        period_start=period_start,
        period_end=period_end,
        order_contributions=order_contributions,
        expense_contributions=expense_contributions,
    )


def _validate_and_build_period(*, store, start_date, end_date):
    if not isinstance(store, Store):
        raise PeriodProfitAggregationError("A server-resolved store is required.")
    if not _is_date_only(start_date) or not _is_date_only(end_date):
        raise PeriodProfitAggregationError("Use whole store-local calendar dates.")
    if end_date < start_date:
        raise PeriodProfitAggregationError("Period end cannot precede period start.")
    timezone = ZoneInfo(store.timezone)
    period_start = datetime.combine(start_date, time.min, tzinfo=timezone)
    period_end = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=timezone,
    )
    return period_start, period_end


def _is_date_only(value) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _event_history_for(order_ids):
    if not order_ids:
        return {}
    history = defaultdict(list)
    for event in (
        OrderStatusEvent.objects.filter(order_id__in=order_ids)
        .filter(
            to_status__in={
                SalesOrder.Status.DELIVERED,
                *TERMINAL_REVERSAL_STATUSES,
            }
        )
        .order_by("occurred_at", "id")
    ):
        history[event.order_id].append(event)
    return history


def _order_contributions(*, delivery_events, reversal_events, event_history):
    contributions = []
    for event in delivery_events:
        _validate_single_delivery(event=event, history=event_history[event.order_id])
        contributions.append(
            ProfitEventContribution(
                event_id=event.pk,
                occurred_at=event.occurred_at,
                contribution=calculate_order_profit_contribution(
                    order=event.order,
                    contribution_type=OrderProfitContributionType.DELIVERY,
                ),
            )
        )
    for event in reversal_events:
        history = event_history[event.order_id]
        delivery_event = _single_delivery_before(event=event, history=history)
        first_reversal = _first_reversal_after(
            delivery_event=delivery_event,
            history=history,
        )
        if event.pk != first_reversal.pk:
            continue
        contributions.append(
            ProfitEventContribution(
                event_id=event.pk,
                occurred_at=event.occurred_at,
                contribution=calculate_order_profit_contribution(
                    order=event.order,
                    contribution_type=OrderProfitContributionType.REVERSAL,
                ),
            )
        )
    return tuple(
        sorted(
            contributions,
            key=lambda row: (row.occurred_at, str(row.event_id)),
        )
    )


def _validate_single_delivery(*, event, history):
    deliveries = [
        recorded_event
        for recorded_event in history
        if recorded_event.to_status == SalesOrder.Status.DELIVERED
    ]
    if len(deliveries) != 1:
        raise PeriodProfitAggregationError(
            "Duplicate delivery evidence prevents a trustworthy profit summary."
        )
    if deliveries[0].pk != event.pk:
        raise PeriodProfitAggregationError(
            "Delivery history does not match the selected period event."
        )


def _single_delivery_before(*, event, history):
    deliveries = [
        recorded_event
        for recorded_event in history
        if (
            recorded_event.to_status == SalesOrder.Status.DELIVERED
            and recorded_event.occurred_at < event.occurred_at
        )
    ]
    if len(deliveries) != 1:
        raise PeriodProfitAggregationError(
            "A reversal requires exactly one earlier delivery event."
        )
    return deliveries[0]


def _first_reversal_after(*, delivery_event, history):
    reversals = [
        recorded_event
        for recorded_event in history
        if (
            recorded_event.to_status in TERMINAL_REVERSAL_STATUSES
            and recorded_event.occurred_at > delivery_event.occurred_at
        )
    ]
    if not reversals:
        raise PeriodProfitAggregationError("A reversal event is missing from history.")
    return reversals[0]


def _summarize(
    *,
    store,
    start_date,
    end_date,
    period_start,
    period_end,
    order_contributions,
    expense_contributions,
):
    contributions = [row.contribution for row in order_contributions]
    net_revenue = _money(
        sum((row.net_revenue_contribution for row in contributions), ZERO_MONEY)
    )
    missing_product_cost = any(
        row.product_cost_contribution is None for row in contributions
    )
    missing_delivery_cost = any(
        row.seller_delivery_cost_contribution is None for row in contributions
    )
    product_cost = (
        None
        if missing_product_cost
        else _money(
            sum(
                (row.product_cost_contribution for row in contributions),
                ZERO_MONEY,
            )
        )
    )
    delivery_cost = (
        None
        if missing_delivery_cost
        else _money(
            sum(
                (row.seller_delivery_cost_contribution for row in contributions),
                ZERO_MONEY,
            )
        )
    )
    operating_cost = _money(
        sum((row.amount for row in expense_contributions), ZERO_MONEY)
    )
    estimated_profit = _estimated_profit(
        net_revenue=net_revenue,
        product_cost=product_cost,
        delivery_cost=delivery_cost,
        operating_cost=operating_cost,
    )
    return PeriodProfitSummary(
        store_id=store.pk,
        start_date=start_date,
        end_date=end_date,
        period_start=period_start,
        period_end=period_end,
        order_contributions=order_contributions,
        expense_contributions=expense_contributions,
        net_revenue=net_revenue,
        product_cost=product_cost,
        seller_delivery_cost=delivery_cost,
        recorded_operating_cost=operating_cost,
        estimated_operational_profit=estimated_profit,
        estimated_profit_margin_percent=_margin(
            net_revenue=net_revenue,
            estimated_profit=estimated_profit,
        ),
        completeness_status=_completeness_status(
            missing_product_cost=missing_product_cost,
            missing_delivery_cost=missing_delivery_cost,
        ),
    )


def _estimated_profit(*, net_revenue, product_cost, delivery_cost, operating_cost):
    if product_cost is None or delivery_cost is None:
        return None
    return _money(net_revenue - product_cost - delivery_cost - operating_cost)


def _margin(*, net_revenue, estimated_profit):
    if estimated_profit is None or net_revenue <= ZERO_MONEY:
        return None
    return (estimated_profit / net_revenue * Decimal("100")).quantize(
        PERCENTAGE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _completeness_status(*, missing_product_cost, missing_delivery_cost):
    if missing_product_cost and missing_delivery_cost:
        return "unavailable_missing_product_and_delivery_cost"
    if missing_product_cost:
        return "unavailable_missing_product_cost"
    if missing_delivery_cost:
        return "unavailable_missing_delivery_cost"
    return "complete"


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
