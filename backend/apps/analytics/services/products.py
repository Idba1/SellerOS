"""Product-level base-delivered sales views built from the shared sales service."""
from dataclasses import dataclass
from datetime import datetime

from apps.accounts.models import Store

from .sales import ProductSalesSummary, summarize_base_delivered_sales


@dataclass(frozen=True)
class ProductPerformanceSummary:
    """Snapshot-based product quantities and gross revenue for one explicit period."""

    period_start: datetime
    period_end: datetime
    products: tuple[ProductSalesSummary, ...]
    data_completeness_status: str
    return_adjustment_status: str


def summarize_product_performance(
    *,
    store: Store,
    period_start: datetime,
    period_end: datetime,
) -> ProductPerformanceSummary:
    """Reuse base-delivered eligibility and arithmetic without adding rankings."""

    sales_summary = summarize_base_delivered_sales(
        store=store,
        period_start=period_start,
        period_end=period_end,
    )
    return ProductPerformanceSummary(
        period_start=sales_summary.period_start,
        period_end=sales_summary.period_end,
        products=sales_summary.products,
        data_completeness_status=sales_summary.data_completeness_status,
        return_adjustment_status=sales_summary.return_adjustment_status,
    )
