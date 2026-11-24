"""Versioned synthetic hand-calculation cases for profit API regression tests."""
from dataclasses import dataclass


PROFIT_CASE_SET_VERSION = "profit-regression-v1"


@dataclass(frozen=True)
class ProfitRegressionCase:
    """One synthetic input shape and independently hand-calculated API outcome."""

    case_id: str
    description: str
    quantity: int | None
    selling_price: str | None
    unit_cost: str | None
    discount: str | None
    seller_delivery_cost: str | None
    recorded_operating_cost: str
    expected_totals: dict[str, str | None]
    expected_completeness_status: str


PROFIT_REGRESSION_CASES = (
    ProfitRegressionCase(
        case_id="discount-delivery-expense",
        description="Known snapshots, saved discount, delivery cost, and one expense.",
        quantity=2,
        selling_price="100.00",
        unit_cost="40.00",
        discount="10.00",
        seller_delivery_cost="15.00",
        recorded_operating_cost="20.00",
        expected_totals={
            "net_revenue": "190.00",
            "product_cost": "80.00",
            "seller_delivery_cost": "15.00",
            "recorded_operating_cost": "20.00",
            "estimated_operational_profit": "75.00",
            "estimated_profit_margin_percent": "39.47",
        },
        expected_completeness_status="complete",
    ),
    ProfitRegressionCase(
        case_id="missing-product-cost",
        description="Known sales and delivery cost, but no item cost snapshot.",
        quantity=1,
        selling_price="100.00",
        unit_cost=None,
        discount="0.00",
        seller_delivery_cost="0.00",
        recorded_operating_cost="12.00",
        expected_totals={
            "net_revenue": "100.00",
            "product_cost": None,
            "seller_delivery_cost": "0.00",
            "recorded_operating_cost": "12.00",
            "estimated_operational_profit": None,
            "estimated_profit_margin_percent": None,
        },
        expected_completeness_status="unavailable_missing_product_cost",
    ),
    ProfitRegressionCase(
        case_id="missing-delivery-cost",
        description="Known sales and item cost, but no seller delivery cost.",
        quantity=1,
        selling_price="100.00",
        unit_cost="40.00",
        discount="0.00",
        seller_delivery_cost=None,
        recorded_operating_cost="12.00",
        expected_totals={
            "net_revenue": "100.00",
            "product_cost": "40.00",
            "seller_delivery_cost": None,
            "recorded_operating_cost": "12.00",
            "estimated_operational_profit": None,
            "estimated_profit_margin_percent": None,
        },
        expected_completeness_status="unavailable_missing_delivery_cost",
    ),
    ProfitRegressionCase(
        case_id="zero-sales-with-expense",
        description="No delivery events and one same-store operating expense.",
        quantity=None,
        selling_price=None,
        unit_cost=None,
        discount=None,
        seller_delivery_cost=None,
        recorded_operating_cost="25.00",
        expected_totals={
            "net_revenue": "0.00",
            "product_cost": "0.00",
            "seller_delivery_cost": "0.00",
            "recorded_operating_cost": "25.00",
            "estimated_operational_profit": "-25.00",
            "estimated_profit_margin_percent": None,
        },
        expected_completeness_status="complete",
    ),
)
