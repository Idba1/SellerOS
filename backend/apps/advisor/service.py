"""Provider-gated advisor explanation orchestration without business arithmetic."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Protocol

from apps.ai.providers.adapter import ProviderTransportError
from apps.ai.providers.configuration import LLMProviderPolicy

from .context import AdvisorContext
from .schemas import ValidatedAdvisorResponse, validate_advisor_output


class AdvisorProvider(Protocol):
    """Future backend-only provider boundary; no implementation is supplied."""

    def generate(self, *, prompt: str, timeout_seconds: int) -> str: ...


def build_advisor_selection_prompt(context: AdvisorContext) -> str:
    """Expose only precomputed metrics and require structured selections.

    It contains no raw orders, customer names/contact values, inventory quantity,
    credentials, or instruction channel for mutation/tool use.
    """

    payload = {
        "sales": {
            "period_start": context.sales.period_start.isoformat(),
            "period_end_exclusive": context.sales.period_end.isoformat(),
            "store_timezone": context.store_timezone,
            "delivered_order_count": context.sales.delivered_order_count,
            "delivered_units": context.sales.delivered_units,
            "delivered_net_sales_before_reversals": format(
                context.sales.delivered_net_sales_before_reversals, ".2f"
            ),
            "data_completeness_status": context.sales.data_completeness_status,
            "return_adjustment_status": context.sales.return_adjustment_status,
        },
        "profit": {
            "start_date": context.profit.start_date.isoformat(),
            "end_date": context.profit.end_date.isoformat(),
            "estimated_operational_profit": _money(
                context.profit.estimated_operational_profit
            ),
            "estimated_profit_margin_percent": _money(
                context.profit.estimated_profit_margin_percent
            ),
            "completeness_status": context.profit.completeness_status,
        },
        "stock": {
            "low_stock_count": context.stock.low_stock_count,
            "configured_threshold_count": context.stock.configured_threshold_count,
        },
        "product": (
            None
            if context.product is None
            else {
                "product_id": str(context.product.product_id),
                "delivered_units": context.product.delivered_units,
                "delivered_gross_sales": _money(
                    context.product.delivered_gross_sales
                ),
                "data_completeness_status": context.product.data_completeness_status,
                "return_adjustment_status": context.product.return_adjustment_status,
            }
        ),
    }
    return "\n".join(
        (
            "Select only supported deterministic advisor insight types.",
            "Do not calculate, invent, rank, forecast, recommend, mutate data, or invoke tools.",
            "Return JSON only: {\"state\":\"explain|abstain\",\"insight_types\":[<supported types>]}",
            "Supported types: base_delivered_sales_snapshot, product_delivery_snapshot, ",
            "estimated_profit_completeness_snapshot, low_stock_threshold_snapshot.",
            "METRIC_CONTEXT:",
            json.dumps(payload, separators=(",", ":")),
        )
    )


def generate_advisor_response(
    context: AdvisorContext,
    *,
    provider: AdvisorProvider,
    policy: LLMProviderPolicy,
) -> ValidatedAdvisorResponse:
    """Call an explicitly approved future provider, then validate its selection.

    Current settings always disable execution before the provider can be touched.
    Transport details are never returned to callers; there are no retries or
    fallbacks that might obscure a provider failure.
    """

    if not policy.execution_enabled:
        return _unavailable("provider_execution_disabled")
    try:
        candidate = provider.generate(
            prompt=build_advisor_selection_prompt(context),
            timeout_seconds=policy.request_timeout_seconds,
        )
    except (TimeoutError, ProviderTransportError):
        return _unavailable("provider_unavailable")
    return validate_advisor_output(context, candidate)


def _money(value: Decimal | None) -> str | None:
    return None if value is None else format(value, ".2f")


def _unavailable(warning: str) -> ValidatedAdvisorResponse:
    return ValidatedAdvisorResponse(
        state="unavailable",
        explanation=None,
        evidence=(),
        warnings=(warning,),
    )
