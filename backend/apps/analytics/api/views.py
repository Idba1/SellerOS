"""Store-scoped public base-sales summary endpoint."""
from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.sales import SalesAggregationError, summarize_base_delivered_sales
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .serializers import serialize_sales_summary


SALES_SUMMARY_QUERY_PARAMETERS = {"period_start", "period_end"}


def parse_aware_timestamp(value, field):
    if value is None:
        raise ValidationError({field: ["This query parameter is required."]})
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            {field: ["Use an ISO 8601 timestamp with a timezone offset."]}
        ) from None
    if timezone.is_naive(parsed):
        raise ValidationError(
            {field: ["Use an ISO 8601 timestamp with a timezone offset."]}
        )
    return parsed


class SalesSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(
            request.query_params,
            SALES_SUMMARY_QUERY_PARAMETERS,
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
