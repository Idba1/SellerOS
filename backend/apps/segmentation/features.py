"""Purchase-derived, non-sensitive features for the SEGMENT-01 policy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.accounts.models import Store
from apps.customers.models import Customer
from apps.customers.services import (
    ELIGIBLE_PURCHASE_STATUSES,
    calculate_order_merchandise_spend,
)
from apps.orders.models import SalesOrder


SEGMENT_RULE_VERSION = "segment-v1"
TRAILING_SPEND_LOOKBACK_DAYS = 365
ZERO_MONEY = Decimal("0.00")


class CustomerFeatureError(ValueError):
    """Safe validation error for unusable feature-calculation inputs."""


@dataclass(frozen=True)
class CustomerBehaviorFeatures:
    """Only behavior facts required by the approved segmentation policy."""

    customer_id: UUID
    as_of: datetime
    store_timezone: str
    segment_rule_version: str
    recorded_purchase_count: int
    last_recorded_purchase_at: datetime | None
    recency_days: int | None
    trailing_365_day_spend_bdt: Decimal


def calculate_customer_behavior_features(
    *, store: Store, customer: Customer, as_of: datetime
) -> CustomerBehaviorFeatures:
    """Calculate reproducible features from one customer's eligible store orders.

    The caller resolves authorization before invoking this service. The explicit
    store/customer comparison prevents accidental cross-store joins; no profile
    name, phone, email, address, or inferred characteristic is returned.
    """

    _validate_inputs(store=store, customer=customer, as_of=as_of)
    store_timezone = ZoneInfo(store.timezone)
    as_of_local_date = as_of.astimezone(store_timezone).date()
    trailing_start_date = as_of_local_date - timedelta(
        days=TRAILING_SPEND_LOOKBACK_DAYS - 1
    )

    eligible_orders = (
        SalesOrder.objects.filter(
            store_id=store.pk,
            customer_id=customer.pk,
            status__in=ELIGIBLE_PURCHASE_STATUSES,
            delivered_at__isnull=False,
            delivered_at__lte=as_of,
        )
        .prefetch_related("items")
        .order_by("delivered_at", "id")
    )

    purchase_count = 0
    last_purchase_at = None
    trailing_spend = ZERO_MONEY
    for order in eligible_orders:
        purchase_count += 1
        last_purchase_at = order.delivered_at
        delivered_local_date = order.delivered_at.astimezone(store_timezone).date()
        if delivered_local_date >= trailing_start_date:
            trailing_spend += calculate_order_merchandise_spend(order)

    recency_days = (
        None
        if last_purchase_at is None
        else (as_of_local_date - last_purchase_at.astimezone(store_timezone).date()).days
    )
    return CustomerBehaviorFeatures(
        customer_id=customer.pk,
        as_of=as_of,
        store_timezone=store.timezone,
        segment_rule_version=SEGMENT_RULE_VERSION,
        recorded_purchase_count=purchase_count,
        last_recorded_purchase_at=last_purchase_at,
        recency_days=recency_days,
        trailing_365_day_spend_bdt=trailing_spend,
    )


def _validate_inputs(*, store: Store, customer: Customer, as_of: datetime) -> None:
    if customer.store_id != store.pk:
        raise CustomerFeatureError("Customer does not belong to the selected store.")
    if timezone.is_naive(as_of):
        raise CustomerFeatureError("Use a timezone-aware as_of timestamp.")
