"""Store-scoped public analytics endpoints using deterministic service results."""
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.products import summarize_product_performance
from apps.analytics.services.sales import SalesAggregationError, summarize_base_delivered_sales
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
