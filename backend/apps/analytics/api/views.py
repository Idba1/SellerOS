"""Store-scoped public analytics endpoints using deterministic service results."""
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from apps.analytics.services.products import summarize_product_performance
from apps.analytics.services.sales import SalesAggregationError, summarize_base_delivered_sales
from apps.inventory.models import StockUnit
from apps.profit.services.period_profit import summarize_period_profit
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .periods import ANALYTICS_PERIOD_QUERY_PARAMETERS, parse_aware_timestamp
from .serializers import serialize_product_performance, serialize_sales_summary


class SalesSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(
            request.query_params,
            ANALYTICS_PERIOD_QUERY_PARAMETERS,
        )
        store = require_authorized_store(request.user)
        period_start = parse_aware_timestamp(
            request.query_params.get("period_start"),
            "period_start",
        )
        period_end = parse_aware_timestamp(
            request.query_params.get("period_end"),
            "period_end",
        )
        try:
            summary = summarize_base_delivered_sales(
                store=store,
                period_start=period_start,
                period_end=period_end,
            )
        except SalesAggregationError as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        return Response(serialize_sales_summary(summary, store_timezone=store.timezone))


class ProductPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(
            request.query_params,
            ANALYTICS_PERIOD_QUERY_PARAMETERS,
        )
        store = require_authorized_store(request.user)
        period_start = parse_aware_timestamp(
            request.query_params.get("period_start"),
            "period_start",
        )
        period_end = parse_aware_timestamp(
            request.query_params.get("period_end"),
            "period_end",
        )
        try:
            summary = summarize_product_performance(
                store=store,
                period_start=period_start,
                period_end=period_end,
            )
        except SalesAggregationError as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        return Response(
            serialize_product_performance(summary, store_timezone=store.timezone)
        )


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, {"start_date", "end_date"})
        from apps.profit.api.periods import parse_profit_period

        start_date, end_date = parse_profit_period(
            start_value=request.query_params.get("start_date"),
            end_value=request.query_params.get("end_date"),
        )
        store = require_authorized_store(request.user)
        timezone = ZoneInfo(store.timezone)
        period_start = datetime.combine(start_date, time.min, tzinfo=timezone)
        period_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone)
        try:
            sales = summarize_base_delivered_sales(store=store, period_start=period_start, period_end=period_end)
            products = summarize_product_performance(store=store, period_start=period_start, period_end=period_end)
            profit = summarize_period_profit(store=store, start_date=start_date, end_date=end_date)
        except SalesAggregationError as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        stock_units = StockUnit.objects.filter(store=store).select_related("product", "variant")
        low_stock = [unit for unit in stock_units if unit.is_low_stock]
        return Response({
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "store_timezone": store.timezone},
            "sales": serialize_sales_summary(sales, store_timezone=store.timezone),
            "products": serialize_product_performance(products, store_timezone=store.timezone),
            "profit": {"net_revenue": f"{profit.net_revenue:.2f}", "estimated_operational_profit": None if profit.estimated_operational_profit is None else f"{profit.estimated_operational_profit:.2f}", "completeness_status": profit.completeness_status},
            "inventory": {"low_stock_count": len(low_stock), "configured_threshold_count": sum(unit.low_stock_threshold is not None for unit in stock_units)},
        })
