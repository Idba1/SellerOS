"""Stable public serialization for base-delivered sales summaries."""
from rest_framework import serializers

from apps.analytics.services.sales import SalesSummary


class ProductSalesSummarySerializer(serializers.Serializer):
    product_id = serializers.UUIDField(read_only=True)
    delivered_units = serializers.IntegerField(read_only=True)
    delivered_gross_sales = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )


def serialize_sales_summary(summary: SalesSummary, *, store_timezone: str):
    """Return a documented response without deriving any extra financial metric."""

    result_state = (
        "data_present"
        if summary.delivered_order_count
        else "no_eligible_events_coverage_unknown"
    )
    return {
        "period": {
            "start": summary.period_start.isoformat(),
            "end_exclusive": summary.period_end.isoformat(),
            "store_timezone": store_timezone,
        },
        "result_state": result_state,
        "totals": {
            "delivered_order_count": summary.delivered_order_count,
            "delivered_units": summary.delivered_units,
            "delivered_gross_sales": f"{summary.delivered_gross_sales:.2f}",
            "delivered_order_discounts": f"{summary.delivered_order_discounts:.2f}",
            "delivered_net_sales_before_reversals": (
                f"{summary.delivered_net_sales_before_reversals:.2f}"
            ),
            "data_completeness_status": summary.data_completeness_status,
            "return_adjustment_status": summary.return_adjustment_status,
        },
        "products": ProductSalesSummarySerializer(
            summary.products,
            many=True,
        ).data,
    }
