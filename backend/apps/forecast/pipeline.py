"""Deterministic daily-demand preparation, evaluation, and safe forecast output."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import sqrt
from statistics import mean
from uuid import UUID
from zoneinfo import ZoneInfo

from apps.accounts.models import Store
from apps.catalog.models import Product
from apps.orders.models import OrderStatusEvent, SalesOrder


POLICY_VERSION = "forecast-v1-daily"
HORIZON_DAYS = 7
MIN_COMPLETE_DAYS = 56
MIN_NONZERO_DAYS = 14
BASELINE_WINDOW_DAYS = 7


@dataclass(frozen=True)
class DailyDemandPoint:
    period_date: date
    units: int


@dataclass(frozen=True)
class DailyDemandSeries:
    store_id: UUID
    product_id: UUID
    start_date: date
    end_date: date
    points: tuple[DailyDemandPoint, ...]
    coverage_complete: bool
    duplicate_delivery_order_count: int
    return_affected_order_count: int


@dataclass(frozen=True)
class ForecastEligibility:
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ForecastEvaluation:
    fold_count: int
    baseline_mae: float | None
    candidate_mae: float | None
    baseline_rmse: float | None
    candidate_rmse: float | None


@dataclass(frozen=True)
class ForecastResult:
    state: str
    policy_version: str
    horizon_days: int
    method: str | None
    estimates: tuple[float, ...]
    eligibility: ForecastEligibility
    evaluation: ForecastEvaluation | None
    limitations: tuple[str, ...]


def build_daily_product_series(
    *, store: Store, product: Product, start_date: date, end_date: date, coverage_complete: bool
) -> DailyDemandSeries:
    """Aggregate immutable delivery events by local day without future fields.

    ``coverage_complete`` is server-owned metadata. It must never be inferred
    from empty delivery rows; false prevents zero-filled history from being used
    for a forecast.
    """
    if product.store_id != store.pk:
        raise ValueError("Product does not belong to the selected store.")
    if end_date < start_date:
        raise ValueError("End date must not be before start date.")
    zone = ZoneInfo(store.timezone)
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    events = list(
        OrderStatusEvent.objects.filter(
            order__store=store,
            to_status=SalesOrder.Status.DELIVERED,
            occurred_at__gte=start,
            occurred_at__lt=end,
            order__items__product=product,
        )
        .select_related("order")
        .prefetch_related("order__items")
        .order_by("occurred_at", "id")
    )
    event_counts: dict[UUID, int] = {}
    for event in events:
        event_counts[event.order_id] = event_counts.get(event.order_id, 0) + 1
    duplicates = {order_id for order_id, count in event_counts.items() if count > 1}
    units_by_day: dict[date, int] = {}
    return_affected_orders: set[UUID] = set()
    for event in events:
        if event.order_id in duplicates:
            continue
        if event.order.status in {SalesOrder.Status.RETURNED, SalesOrder.Status.REFUNDED}:
            return_affected_orders.add(event.order_id)
        local_day = event.occurred_at.astimezone(zone).date()
        units_by_day[local_day] = units_by_day.get(local_day, 0) + sum(
            item.quantity for item in event.order.items.all() if item.product_id == product.pk
        )
    points = []
    cursor = start_date
    while cursor <= end_date:
        points.append(DailyDemandPoint(cursor, units_by_day.get(cursor, 0)))
        cursor += timedelta(days=1)
    return DailyDemandSeries(
        store_id=store.pk,
        product_id=product.pk,
        start_date=start_date,
        end_date=end_date,
        points=tuple(points),
        coverage_complete=coverage_complete,
        duplicate_delivery_order_count=len(duplicates),
        return_affected_order_count=len(return_affected_orders),
    )


def assess_eligibility(series: DailyDemandSeries) -> ForecastEligibility:
    reasons: list[str] = []
    if not series.coverage_complete:
        reasons.append("history_coverage_unknown")
    if series.duplicate_delivery_order_count:
        reasons.append("duplicate_delivery_evidence")
    if series.return_affected_order_count:
        reasons.append("return_treatment_not_supported")
    if len(series.points) < MIN_COMPLETE_DAYS:
        reasons.append("fewer_than_56_complete_days")
    if sum(point.units > 0 for point in series.points) < MIN_NONZERO_DAYS:
        reasons.append("fewer_than_14_nonzero_days")
    return ForecastEligibility(eligible=not reasons, reasons=tuple(reasons))


def evaluate_chronologically(series: DailyDemandSeries) -> ForecastEvaluation:
    """Evaluate only past-to-future folds; no shuffle or final-test tuning."""
    eligibility = assess_eligibility(series)
    if not eligibility.eligible or len(series.points) < MIN_COMPLETE_DAYS + HORIZON_DAYS:
        return ForecastEvaluation(0, None, None, None, None)
    baseline_errors: list[float] = []
    candidate_errors: list[float] = []
    for cutoff in range(MIN_COMPLETE_DAYS, len(series.points) - HORIZON_DAYS + 1, HORIZON_DAYS):
        train = [point.units for point in series.points[:cutoff]]
        actual = [point.units for point in series.points[cutoff : cutoff + HORIZON_DAYS]]
        baseline = _moving_average(train)
        candidate = _seasonal_naive(train)
        baseline_errors.extend(abs(value - baseline) for value in actual)
        candidate_errors.extend(abs(value - prediction) for value, prediction in zip(actual, candidate))
    return ForecastEvaluation(
        fold_count=len(baseline_errors) // HORIZON_DAYS,
        baseline_mae=mean(baseline_errors),
        candidate_mae=mean(candidate_errors),
        baseline_rmse=sqrt(mean(error * error for error in baseline_errors)),
        candidate_rmse=sqrt(mean(error * error for error in candidate_errors)),
    )


def forecast_product_demand(series: DailyDemandSeries) -> ForecastResult:
    """Return an estimate only after the fixed, observable v1 gate passes."""
    eligibility = assess_eligibility(series)
    if not eligibility.eligible:
        return ForecastResult(
            state="insufficient_history",
            policy_version=POLICY_VERSION,
            horizon_days=HORIZON_DAYS,
            method=None,
            estimates=(),
            eligibility=eligibility,
            evaluation=None,
            limitations=eligibility.reasons,
        )
    evaluation = evaluate_chronologically(series)
    history = [point.units for point in series.points]
    baseline = _moving_average(history)
    candidate = _seasonal_naive(history)
    use_candidate = (
        evaluation.fold_count > 0
        and evaluation.candidate_mae is not None
        and evaluation.baseline_mae is not None
        and evaluation.candidate_mae < evaluation.baseline_mae
    )
    return ForecastResult(
        state="available",
        policy_version=POLICY_VERSION,
        horizon_days=HORIZON_DAYS,
        method="seasonal_naive_7_day" if use_candidate else "trailing_7_day_mean",
        estimates=tuple(candidate if use_candidate else [baseline] * HORIZON_DAYS),
        eligibility=eligibility,
        evaluation=evaluation,
        limitations=("synthetic_or_authorized_history_only",),
    )


def _moving_average(history: list[int]) -> float:
    return mean(history[-BASELINE_WINDOW_DAYS:])


def _seasonal_naive(history: list[int]) -> list[float]:
    return [float(value) for value in history[-HORIZON_DAYS:]]
