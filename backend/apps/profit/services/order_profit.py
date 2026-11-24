"""Order snapshot contribution arithmetic for estimated operational profit."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from apps.orders.models import OrderItem, SalesOrder


MONEY_QUANTUM = Decimal("0.01")
PERCENTAGE_QUANTUM = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")


class OrderProfitCalculationError(ValueError):
    """Raised when persisted order evidence cannot produce a safe contribution."""


class OrderProfitContributionType(StrEnum):
    """The event contribution being calculated; event selection remains external."""

    DELIVERY = "delivery"
    REVERSAL = "reversal"


@dataclass(frozen=True)
class OrderItemProfitContribution:
    """One order-line contribution calculated only from transaction snapshots."""

    order_item_id: object
    product_id: object
    quantity: int
    gross_revenue: Decimal
    discount_allocation: Decimal
    net_revenue_contribution: Decimal
    product_cost_contribution: Decimal | None


@dataclass(frozen=True)
class OrderProfitContribution:
    """One delivery or full-order reversal before store-level operating expenses."""

    order_id: object
    contribution_type: OrderProfitContributionType
    items: tuple[OrderItemProfitContribution, ...]
    gross_revenue: Decimal
    discount_total: Decimal
    net_revenue_contribution: Decimal
    product_cost_contribution: Decimal | None
    seller_delivery_cost_contribution: Decimal | None
    estimated_contribution_before_operating_expenses: Decimal | None
    estimated_margin_percent: Decimal | None
    completeness_status: str


def calculate_order_profit_contribution(
    *,
    order: SalesOrder,
    contribution_type: OrderProfitContributionType
    | str = OrderProfitContributionType.DELIVERY,
) -> OrderProfitContribution:
    """Calculate an order event's signed contribution from immutable snapshots.

    The caller is responsible for selecting an authorized order and the eligible
    delivery/reversal event. General operating expenses are intentionally not
    allocated to orders. A reversal negates revenue and COGS but not an already
    consumed outbound delivery cost, as approved in PROFIT-01.
    """

    if not isinstance(order, SalesOrder):
        raise OrderProfitCalculationError("A persisted SalesOrder is required.")
    try:
        normalized_type = OrderProfitContributionType(contribution_type)
    except ValueError as error:
        raise OrderProfitCalculationError(
            "Contribution type must be delivery or reversal."
        ) from error

    if order.currency_code != "BDT":
        raise OrderProfitCalculationError("SellerOS profit contributions require BDT.")

    items = tuple(order.items.all().order_by("id"))
    if not items:
        raise OrderProfitCalculationError("An order requires at least one item.")

    _validate_order_discount(order, items)
    sign = (
        Decimal("-1")
        if normalized_type is OrderProfitContributionType.REVERSAL
        else Decimal("1")
    )
    item_contributions = tuple(
        _calculate_item_contribution(item=item, sign=sign) for item in items
    )
    gross_revenue = _money(
        sum((item.gross_revenue for item in item_contributions), ZERO_MONEY)
    )
    discount_total = _money(
        sum((item.discount_allocation for item in item_contributions), ZERO_MONEY)
    )
    net_revenue = _money(
        sum(
            (item.net_revenue_contribution for item in item_contributions),
            ZERO_MONEY,
        )
    )
    missing_product_cost = any(
        item.product_cost_contribution is None for item in item_contributions
    )
    product_cost = (
        None
        if missing_product_cost
        else _money(
            sum(
                (item.product_cost_contribution for item in item_contributions),
                ZERO_MONEY,
            )
        )
    )
    delivery_cost = _delivery_cost_contribution(
        order=order,
        contribution_type=normalized_type,
    )
    completeness_status = _completeness_status(
        missing_product_cost=missing_product_cost,
        delivery_cost=delivery_cost,
        contribution_type=normalized_type,
    )
    estimated_contribution = _estimated_contribution(
        net_revenue=net_revenue,
        product_cost=product_cost,
        delivery_cost=delivery_cost,
    )
    margin = _margin(
        net_revenue=net_revenue,
        estimated_contribution=estimated_contribution,
    )
    return OrderProfitContribution(
        order_id=order.pk,
        contribution_type=normalized_type,
        items=item_contributions,
        gross_revenue=gross_revenue,
        discount_total=discount_total,
        net_revenue_contribution=net_revenue,
        product_cost_contribution=product_cost,
        seller_delivery_cost_contribution=delivery_cost,
        estimated_contribution_before_operating_expenses=estimated_contribution,
        estimated_margin_percent=margin,
        completeness_status=completeness_status,
    )


def _calculate_item_contribution(
    *,
    item: OrderItem,
    sign: Decimal,
) -> OrderItemProfitContribution:
    gross_revenue = _money(item.quantity * item.selling_price_snapshot)
    if item.discount_allocation > gross_revenue:
        raise OrderProfitCalculationError(
            "An order-item discount cannot exceed that item's gross revenue."
        )
    net_revenue = _money((gross_revenue - item.discount_allocation) * sign)
    product_cost = (
        None
        if item.unit_cost_snapshot is None
        else _money(item.quantity * item.unit_cost_snapshot * sign)
    )
    return OrderItemProfitContribution(
        order_item_id=item.pk,
        product_id=item.product_id,
        quantity=item.quantity,
        gross_revenue=gross_revenue,
        discount_allocation=_money(item.discount_allocation),
        net_revenue_contribution=net_revenue,
        product_cost_contribution=product_cost,
    )


def _validate_order_discount(order: SalesOrder, items: tuple[OrderItem, ...]) -> None:
    allocated_discount = _money(
        sum((item.discount_allocation for item in items), ZERO_MONEY)
    )
    if allocated_discount != _money(order.order_discount):
        raise OrderProfitCalculationError(
            "Order-item discount allocations must equal the order discount."
        )


def _delivery_cost_contribution(
    *,
    order: SalesOrder,
    contribution_type: OrderProfitContributionType,
) -> Decimal | None:
    if contribution_type is OrderProfitContributionType.REVERSAL:
        return ZERO_MONEY
    if order.seller_delivery_cost is None:
        return None
    return _money(order.seller_delivery_cost)


def _completeness_status(
    *,
    missing_product_cost: bool,
    delivery_cost: Decimal | None,
    contribution_type: OrderProfitContributionType,
) -> str:
    missing_delivery_cost = (
        contribution_type is OrderProfitContributionType.DELIVERY
        and delivery_cost is None
    )
    if missing_product_cost and missing_delivery_cost:
        return "unavailable_missing_product_and_delivery_cost"
    if missing_product_cost:
        return "unavailable_missing_product_cost"
    if missing_delivery_cost:
        return "unavailable_missing_delivery_cost"
    return "complete"


def _estimated_contribution(
    *,
    net_revenue: Decimal,
    product_cost: Decimal | None,
    delivery_cost: Decimal | None,
) -> Decimal | None:
    if product_cost is None or delivery_cost is None:
        return None
    return _money(net_revenue - product_cost - delivery_cost)


def _margin(
    *,
    net_revenue: Decimal,
    estimated_contribution: Decimal | None,
) -> Decimal | None:
    if estimated_contribution is None or net_revenue <= ZERO_MONEY:
        return None
    return (estimated_contribution / net_revenue * Decimal("100")).quantize(
        PERCENTAGE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
