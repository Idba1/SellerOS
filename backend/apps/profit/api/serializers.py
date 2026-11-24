"""Stable JSON representations for estimated-profit summaries and their basis."""
from decimal import Decimal

from apps.profit.services.period_profit import PeriodProfitSummary


def serialize_period_profit(summary: PeriodProfitSummary, *, store_timezone: str):
    """Expose deterministic inputs and limitations without a certainty claim."""

    return {
        "period": {
            "start_date": summary.start_date.isoformat(),
            "end_date": summary.end_date.isoformat(),
            "start": summary.period_start.isoformat(),
            "end_exclusive": summary.period_end.isoformat(),
            "store_timezone": store_timezone,
        },
        "totals": {
            "net_revenue": _money(summary.net_revenue),
            "product_cost": _money(summary.product_cost),
            "seller_delivery_cost": _money(summary.seller_delivery_cost),
            "recorded_operating_cost": _money(summary.recorded_operating_cost),
            "estimated_operational_profit": _money(
                summary.estimated_operational_profit
            ),
            "estimated_profit_margin_percent": _money(
                summary.estimated_profit_margin_percent
            ),
        },
        "completeness": {
            "status": summary.completeness_status,
            "profit_available": summary.estimated_operational_profit is not None,
            "warnings": _warnings(summary),
        },
        "calculation_basis": {
            "formula": (
                "net revenue - product cost - seller delivery cost "
                "- recorded operating cost"
            ),
            "revenue": (
                "Immutable delivery order-line price snapshots less saved "
                "discount allocations."
            ),
            "product_cost": (
                "Immutable order-line unit-cost snapshots; missing snapshots "
                "suppress profit."
            ),
            "delivery_cost": (
                "Stored seller delivery cost once per delivery; full-order "
                "reversals do not reverse it."
            ),
            "return_refund": (
                "The first terminal RETURNED or REFUNDED event reverses "
                "full-order revenue and COGS once in that event's period."
            ),
            "operating_expenses": (
                "Same-store seller-entered expenses incurred in the selected "
                "dates, deducted once at store aggregate level."
            ),
            "rounding": (
                "BDT Decimal values are rounded to two places using ROUND_HALF_UP."
            ),
            "excluded_components": [
                "tax",
                "payment_gateway_fees",
                "customer_paid_shipping",
                "unrecorded_courier_settlements",
                "cash_collection",
                "inventory_shrinkage",
                "unrecorded_return_shipping",
            ],
        },
        "included_records": {
            "order_events": [
                {
                    "event_id": str(row.event_id),
                    "occurred_at": row.occurred_at.isoformat(),
                    "order_id": str(row.contribution.order_id),
                    "contribution_type": row.contribution.contribution_type.value,
                    "net_revenue_contribution": _money(
                        row.contribution.net_revenue_contribution
                    ),
                    "product_cost_contribution": _money(
                        row.contribution.product_cost_contribution
                    ),
                    "seller_delivery_cost_contribution": _money(
                        row.contribution.seller_delivery_cost_contribution
                    ),
                    "estimated_contribution_before_operating_expenses": _money(
                        row.contribution.estimated_contribution_before_operating_expenses
                    ),
                    "completeness_status": row.contribution.completeness_status,
                }
                for row in summary.order_contributions
            ],
            "expenses": [
                {
                    "expense_id": str(row.expense_id),
                    "incurred_on": row.incurred_on.isoformat(),
                    "amount": _money(row.amount),
                }
                for row in summary.expense_contributions
            ],
        },
    }


def _warnings(summary: PeriodProfitSummary) -> list[str]:
    warnings = [
        "Estimated operational profit is not a tax, cash-flow, or formal "
        "accounting statement."
    ]
    if summary.product_cost is None:
        warnings.append(
            "At least one included order item has no product-cost snapshot; "
            "profit and margin are unavailable."
        )
    if summary.seller_delivery_cost is None:
        warnings.append(
            "At least one included delivery has no seller delivery cost; "
            "profit and margin are unavailable."
        )
    return warnings


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"
