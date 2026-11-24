"""Read-only customer summaries derived from recorded sales orders."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from apps.customers.models import Customer
from apps.orders.models import SalesOrder


ELIGIBLE_PURCHASE_STATUSES = {
    SalesOrder.Status.DELIVERED,
    SalesOrder.Status.RETURN_REQUESTED,
}


@dataclass(frozen=True)
class CustomerPurchaseHistory:
    """Current recognized purchase facts; no customer-level values are persisted."""

    purchase_count: int
    last_purchase_at: datetime | None
    total_spend: Decimal


def calculate_order_merchandise_spend(order: SalesOrder) -> Decimal:
    """Return the immutable merchandise amount used by customer-derived facts.

    Callers must provide an order scoped by the server and may prefetch ``items``
    to avoid per-order queries. Seller delivery cost, tax, payment state, and
    current catalogue prices are deliberately excluded.
    """

    line_gross = sum(
        (item.quantity * item.selling_price_snapshot for item in order.items.all()),
        Decimal("0.00"),
    )
    return line_gross - order.order_discount


def get_customer_purchase_history(customer: Customer) -> CustomerPurchaseHistory:
    """Calculate recognized customer purchases from the order ledger.

    A delivered sale remains eligible while a return is only requested. A fully
    returned/refunded order is excluded because the approved first-prototype
    rule reverses its completed-sale merchandise value once.
    """

    orders = (
        SalesOrder.objects.filter(
            store_id=customer.store_id,
            customer_id=customer.pk,
            status__in=ELIGIBLE_PURCHASE_STATUSES,
            delivered_at__isnull=False,
        )
        .prefetch_related("items")
        .order_by("delivered_at", "id")
    )

    total_spend = Decimal("0.00")
    purchase_count = 0
    last_purchase_at = None
    for order in orders:
        total_spend += calculate_order_merchandise_spend(order)
        purchase_count += 1
        last_purchase_at = order.delivered_at

    return CustomerPurchaseHistory(
        purchase_count=purchase_count,
        last_purchase_at=last_purchase_at,
        total_spend=total_spend,
    )
