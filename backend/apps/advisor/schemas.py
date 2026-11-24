"""Evidence-bound validation for structured advisor insight selection."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .context import AdvisorContext


SUPPORTED_INSIGHT_TYPES = {
    "base_delivered_sales_snapshot",
    "product_delivery_snapshot",
    "estimated_profit_completeness_snapshot",
    "low_stock_threshold_snapshot",
}


@dataclass(frozen=True)
class AdvisorMetricEvidence:
    source_endpoint: str
    metric_fields: tuple[str, ...]
    scope: str
    period_kind: str
    period_start: str | None
    period_end: str | None
    timezone: str | None


@dataclass(frozen=True)
class ValidatedAdvisorResponse:
    state: str
    explanation: str | None
    evidence: tuple[AdvisorMetricEvidence, ...]
    warnings: tuple[str, ...]


def validate_advisor_output(
    context: AdvisorContext, candidate: str | Mapping[str, Any]
) -> ValidatedAdvisorResponse:
    """Render only supported, source-backed insight selections.

    The provider cannot supply a free-text business claim. An invalid, unknown,
    duplicate, or context-incompatible selection becomes an abstention rather
    than an explanation with a fabricated value.
    """

    payload = _parse_candidate(candidate)
    if payload is None or set(payload) != {"state", "insight_types"}:
        return _abstention("invalid_provider_output")
    state = payload.get("state")
    insight_types = payload.get("insight_types")
    if state == "abstain" and insight_types == []:
        return _abstention("provider_abstained")
    if state != "explain" or not isinstance(insight_types, list) or not insight_types:
        return _abstention("invalid_provider_output")
    if any(not isinstance(item, str) for item in insight_types):
        return _abstention("invalid_provider_output")
    if len(set(insight_types)) != len(insight_types):
        return _abstention("invalid_provider_output")
    if not set(insight_types).issubset(SUPPORTED_INSIGHT_TYPES):
        return _abstention("unsupported_insight_type")
    if "product_delivery_snapshot" in insight_types and context.product is None:
        return _abstention("missing_product_evidence")

    explanations: list[str] = []
    evidence: list[AdvisorMetricEvidence] = []
    warnings: list[str] = []
    for insight_type in insight_types:
        explanation, item_evidence, item_warnings = _render_insight(
            context, insight_type
        )
        explanations.append(explanation)
        evidence.append(item_evidence)
        warnings.extend(item_warnings)
    return ValidatedAdvisorResponse(
        state="explanation",
        explanation=" ".join(explanations),
        evidence=tuple(evidence),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _parse_candidate(candidate: str | Mapping[str, Any]) -> Mapping[str, Any] | None:
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError:
            return None
    return candidate if isinstance(candidate, Mapping) else None


def _render_insight(
    context: AdvisorContext, insight_type: str
) -> tuple[str, AdvisorMetricEvidence, tuple[str, ...]]:
    if insight_type == "base_delivered_sales_snapshot":
        sales = context.sales
        return (
            (
                f"For delivery events from {sales.period_start.isoformat()} through before "
                f"{sales.period_end.isoformat()} ({context.store_timezone}), base delivered "
                f"net sales were BDT {sales.delivered_net_sales_before_reversals:.2f} from "
                f"{sales.delivered_order_count} delivered orders and {sales.delivered_units} units."
            ),
            AdvisorMetricEvidence(
                source_endpoint="/api/v1/analytics/sales-summary/",
                metric_fields=(
                    "delivered_net_sales_before_reversals",
                    "delivered_order_count",
                    "delivered_units",
                    "data_completeness_status",
                    "return_adjustment_status",
                ),
                scope="explicit delivery-event interval",
                period_kind="half_open_delivery_event_interval",
                period_start=sales.period_start.isoformat(),
                period_end=sales.period_end.isoformat(),
                timezone=context.store_timezone,
            ),
            (
                f"data_completeness_status:{sales.data_completeness_status}",
                f"return_adjustment_status:{sales.return_adjustment_status}",
                "base_delivered_sales_not_retained_sales",
            ),
        )
    if insight_type == "product_delivery_snapshot":
        product = context.product
        return (
            (
                f"Product record {product.product_id} had {product.delivered_units} delivered "
                f"units and BDT {product.delivered_gross_sales:.2f} base delivered gross sales "
                "in the selected delivery-event period."
            ),
            AdvisorMetricEvidence(
                source_endpoint="/api/v1/analytics/product-performance/",
                metric_fields=(
                    "product_id",
                    "delivered_units",
                    "delivered_gross_sales",
                    "return_adjustment_status",
                ),
                scope="explicit delivery-event interval for one product record",
                period_kind="half_open_delivery_event_interval",
                period_start=context.sales.period_start.isoformat(),
                period_end=context.sales.period_end.isoformat(),
                timezone=context.store_timezone,
            ),
            (
                f"data_completeness_status:{product.data_completeness_status}",
                f"return_adjustment_status:{product.return_adjustment_status}",
                "product_sales_not_profit_ranking_forecast_or_recommendation",
            ),
        )
    if insight_type == "estimated_profit_completeness_snapshot":
        profit = context.profit
        evidence = AdvisorMetricEvidence(
            source_endpoint="/api/v1/profit/summary/",
            metric_fields=(
                "estimated_operational_profit",
                "estimated_profit_margin_percent",
                "completeness.status",
            ),
            scope="inclusive store-local business dates",
            period_kind="inclusive_store_local_date_range",
            period_start=profit.start_date.isoformat(),
            period_end=profit.end_date.isoformat(),
            timezone=context.store_timezone,
        )
        base_warning = "estimated_profit_not_tax_cash_flow_payout_or_formal_accounting"
        if profit.estimated_operational_profit is None:
            return (
                (
                    "Estimated operational profit is unavailable for store-local dates "
                    f"{profit.start_date.isoformat()} through {profit.end_date.isoformat()} "
                    f"because {profit.completeness_status}."
                ),
                evidence,
                (base_warning, f"profit_completeness_status:{profit.completeness_status}"),
            )
        margin_sentence = (
            " Estimated margin is unavailable."
            if profit.estimated_profit_margin_percent is None
            else f" Estimated margin is {profit.estimated_profit_margin_percent:.2f}%."
        )
        return (
            (
                "Estimated operational profit for store-local dates "
                f"{profit.start_date.isoformat()} through {profit.end_date.isoformat()} is "
                f"BDT {profit.estimated_operational_profit:.2f}."
                f"{margin_sentence}"
            ),
            evidence,
            (base_warning, f"profit_completeness_status:{profit.completeness_status}"),
        )
    stock = context.stock
    return (
        (
            f"{stock.low_stock_count} current stock units are at or below their configured "
            f"threshold; {stock.configured_threshold_count} units have a configured threshold."
        ),
        AdvisorMetricEvidence(
            source_endpoint="/api/v1/analytics/dashboard/",
            metric_fields=("inventory.low_stock_count", "inventory.configured_threshold_count"),
            scope="current inventory state, not a sales-period metric",
            period_kind="current_state",
            period_start=None,
            period_end=None,
            timezone=context.store_timezone,
        ),
        ("current_stock_not_demand_forecast_or_reorder_recommendation",),
    )


def _abstention(warning: str) -> ValidatedAdvisorResponse:
    return ValidatedAdvisorResponse(
        state="abstain",
        explanation=None,
        evidence=(),
        warnings=(warning,),
    )
