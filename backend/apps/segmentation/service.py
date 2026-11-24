"""Explainable assignment for the approved deterministic segment rules."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from apps.accounts.models import Store
from apps.customers.models import Customer

from .features import (
    SEGMENT_RULE_VERSION,
    CustomerBehaviorFeatures,
    calculate_customer_behavior_features,
)


NEW_RECENCY_DAYS_MAXIMUM = 30
ACTIVE_RECENCY_DAYS_MAXIMUM = 90
HIGH_VALUE_MINIMUM_PURCHASE_COUNT = 2
HIGH_VALUE_SPEND_BDT = Decimal("10000.00")


class CustomerSegment(str, Enum):
    NO_RECORDED_ELIGIBLE_PURCHASE = "NO_RECORDED_ELIGIBLE_PURCHASE"
    INACTIVE = "INACTIVE"
    HIGH_VALUE = "HIGH_VALUE"
    REPEAT = "REPEAT"
    NEW = "NEW"
    ACTIVE_ONE_TIME = "ACTIVE_ONE_TIME"


class CustomerSegmentError(ValueError):
    """Safe error for inconsistent feature facts or rule versions."""


@dataclass(frozen=True)
class CustomerSegmentAssignment:
    """One explainable label backed by the exact feature values used."""

    segment: CustomerSegment
    rule_version: str
    features: CustomerBehaviorFeatures
    explanation: str


def calculate_customer_segment(
    *, store: Store, customer: Customer, as_of
) -> CustomerSegmentAssignment:
    """Build same-store features first, then assign the documented label."""

    features = calculate_customer_behavior_features(
        store=store,
        customer=customer,
        as_of=as_of,
    )
    return assign_customer_segment(features)


def assign_customer_segment(
    features: CustomerBehaviorFeatures,
) -> CustomerSegmentAssignment:
    """Apply SEGMENT-01 precedence without scoring, prediction, or mutation."""

    _validate_feature_basis(features)
    if features.recorded_purchase_count == 0:
        return _assignment(
            CustomerSegment.NO_RECORDED_ELIGIBLE_PURCHASE,
            features,
            "No eligible purchase is recorded in this store ledger as of the selected "
            "time. This does not establish lifetime or new-customer status.",
        )

    recency_days = features.recency_days
    if recency_days is None:
        raise CustomerSegmentError("Purchase history has incomplete recency evidence.")
    if recency_days > ACTIVE_RECENCY_DAYS_MAXIMUM:
        return _assignment(
            CustomerSegment.INACTIVE,
            features,
            f"The most recent eligible recorded purchase was {recency_days} local "
            "calendar days ago, outside the 90-day active window.",
        )
    if (
        features.recorded_purchase_count >= HIGH_VALUE_MINIMUM_PURCHASE_COUNT
        and features.trailing_365_day_spend_bdt >= HIGH_VALUE_SPEND_BDT
    ):
        return _assignment(
            CustomerSegment.HIGH_VALUE,
            features,
            f"{features.recorded_purchase_count} eligible recorded purchases and BDT "
            f"{features.trailing_365_day_spend_bdt:.2f} in trailing 365-day merchandise "
            "spend meet the active high-value rule.",
        )
    if features.recorded_purchase_count >= HIGH_VALUE_MINIMUM_PURCHASE_COUNT:
        return _assignment(
            CustomerSegment.REPEAT,
            features,
            f"{features.recorded_purchase_count} eligible recorded purchases are within "
            f"the active 90-day window; trailing 365-day merchandise spend is BDT "
            f"{features.trailing_365_day_spend_bdt:.2f}, below the high-value threshold.",
        )
    if recency_days <= NEW_RECENCY_DAYS_MAXIMUM:
        return _assignment(
            CustomerSegment.NEW,
            features,
            f"One eligible recorded purchase occurred {recency_days} local calendar days "
            "ago, within the 30-day new-customer window.",
        )
    return _assignment(
        CustomerSegment.ACTIVE_ONE_TIME,
        features,
        f"One eligible recorded purchase occurred {recency_days} local calendar days ago, "
        "inside the active 90-day window but outside the 30-day new-customer window.",
    )


def _assignment(
    segment: CustomerSegment,
    features: CustomerBehaviorFeatures,
    explanation: str,
) -> CustomerSegmentAssignment:
    return CustomerSegmentAssignment(
        segment=segment,
        rule_version=SEGMENT_RULE_VERSION,
        features=features,
        explanation=explanation,
    )


def _validate_feature_basis(features: CustomerBehaviorFeatures) -> None:
    if features.segment_rule_version != SEGMENT_RULE_VERSION:
        raise CustomerSegmentError("Unsupported customer feature rule version.")
    if features.recorded_purchase_count < 0:
        raise CustomerSegmentError("Purchase count cannot be negative.")
    if features.recorded_purchase_count == 0:
        if features.last_recorded_purchase_at is not None or features.recency_days is not None:
            raise CustomerSegmentError("Empty purchase history has inconsistent recency.")
        return
    if features.last_recorded_purchase_at is None or features.recency_days is None:
        raise CustomerSegmentError("Purchase history has incomplete recency evidence.")
    if features.recency_days < 0:
        raise CustomerSegmentError("Purchase recency cannot be negative.")
