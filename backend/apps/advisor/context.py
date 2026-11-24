"""Bounded same-store advisor context built from existing deterministic services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from apps.accounts.models import Account
from apps.analytics.services.products import summarize_product_performance
from apps.analytics.services.sales import summarize_base_delivered_sales
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.customers.services import get_customer_purchase_history
from apps.inventory.services import StockThresholdSummary, summarize_stock_thresholds
from apps.profit.services.period_profit import summarize_period_profit
from core.permissions import require_authorized_store


class AdvisorContextError(ValueError):
    """Safe error for absent/foreign optional advisor evidence."""


@dataclass(frozen=True)
class AdvisorSalesContext:
    period_start: datetime
    period_end: datetime
    delivered_order_count: int
    delivered_units: int
    delivered_gross_sales: Decimal
    delivered_order_discounts: Decimal
    delivered_net_sales_before_reversals: Decimal
    data_completeness_status: str
    return_adjustment_status: str


@dataclass(frozen=True)
class AdvisorProfitContext:
    start_date: date
    end_date: date
    net_revenue: Decimal
    product_cost: Decimal | None
    seller_delivery_cost: Decimal | None
    recorded_operating_cost: Decimal
    estimated_operational_profit: Decimal | None
    estimated_profit_margin_percent: Decimal | None
    completeness_status: str


@dataclass(frozen=True)
class AdvisorProductContext:
    product_id: UUID
    delivered_units: int
    delivered_gross_sales: Decimal
    data_completeness_status: str
    return_adjustment_status: str


@dataclass(frozen=True)
class AdvisorCustomerContext:
    """Opaque customer ledger facts only; no name, email, or phone is included."""

    customer_id: UUID
    purchase_count: int
    last_purchase_at: datetime | None
    total_spend: Decimal


@dataclass(frozen=True)
class AdvisorContext:
    """Minimal deterministic evidence for a future seller-reviewable advisor."""

    store_id: UUID
    store_timezone: str
    sales: AdvisorSalesContext
    profit: AdvisorProfitContext
    stock: StockThresholdSummary
    product: AdvisorProductContext | None
    customer: AdvisorCustomerContext | None


def build_advisor_context(
    account: Account,
    *,
    start_date: date,
    end_date: date,
    product_id: UUID | None = None,
    customer_id: UUID | None = None,
) -> AdvisorContext:
    """Reuse service outputs for one authorized store and one bounded period.

    The profit service validates the whole store-local date interval and supplies
    its derived aware boundaries to sales/product services. Optional product and
    customer records are resolved only inside the server-authorized store.
    """

    store = require_authorized_store(account)
    profit_summary = summarize_period_profit(
        store=store,
        start_date=start_date,
        end_date=end_date,
    )
    sales_summary = summarize_base_delivered_sales(
        store=store,
        period_start=profit_summary.period_start,
        period_end=profit_summary.period_end,
    )
    product_context = _build_product_context(
        store=store,
        product_id=product_id,
        period_start=profit_summary.period_start,
        period_end=profit_summary.period_end,
    )
    customer_context = _build_customer_context(store=store, customer_id=customer_id)

    return AdvisorContext(
        store_id=store.pk,
        store_timezone=store.timezone,
        sales=AdvisorSalesContext(
            period_start=sales_summary.period_start,
            period_end=sales_summary.period_end,
            delivered_order_count=sales_summary.delivered_order_count,
            delivered_units=sales_summary.delivered_units,
            delivered_gross_sales=sales_summary.delivered_gross_sales,
            delivered_order_discounts=sales_summary.delivered_order_discounts,
            delivered_net_sales_before_reversals=(
                sales_summary.delivered_net_sales_before_reversals
            ),
            data_completeness_status=sales_summary.data_completeness_status,
            return_adjustment_status=sales_summary.return_adjustment_status,
        ),
        profit=AdvisorProfitContext(
            start_date=profit_summary.start_date,
            end_date=profit_summary.end_date,
            net_revenue=profit_summary.net_revenue,
            product_cost=profit_summary.product_cost,
            seller_delivery_cost=profit_summary.seller_delivery_cost,
            recorded_operating_cost=profit_summary.recorded_operating_cost,
            estimated_operational_profit=profit_summary.estimated_operational_profit,
            estimated_profit_margin_percent=(
                profit_summary.estimated_profit_margin_percent
            ),
            completeness_status=profit_summary.completeness_status,
        ),
        stock=summarize_stock_thresholds(store=store),
        product=product_context,
        customer=customer_context,
    )


def _build_product_context(*, store, product_id, period_start, period_end):
    if product_id is None:
        return None
    if not Product.objects.filter(store=store, pk=product_id).exists():
        raise AdvisorContextError("No authorized product evidence was found.")
    summary = summarize_product_performance(
        store=store,
        period_start=period_start,
        period_end=period_end,
    )
    product_summary = next(
        (row for row in summary.products if row.product_id == product_id),
        None,
    )
    if product_summary is None:
        return None
    return AdvisorProductContext(
        product_id=product_summary.product_id,
        delivered_units=product_summary.delivered_units,
        delivered_gross_sales=product_summary.delivered_gross_sales,
        data_completeness_status=summary.data_completeness_status,
        return_adjustment_status=summary.return_adjustment_status,
    )


def _build_customer_context(*, store, customer_id):
    if customer_id is None:
        return None
    try:
        customer = Customer.objects.get(store=store, pk=customer_id)
    except Customer.DoesNotExist as error:
        raise AdvisorContextError("No authorized customer evidence was found.") from error
    history = get_customer_purchase_history(customer)
    return AdvisorCustomerContext(
        customer_id=customer.pk,
        purchase_count=history.purchase_count,
        last_purchase_at=history.last_purchase_at,
        total_spend=history.total_spend,
    )
