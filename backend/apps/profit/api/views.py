"""Authenticated store-scoped profit-summary API."""
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profit.services.order_profit import OrderProfitCalculationError
from apps.profit.services.period_profit import (
    PeriodProfitAggregationError,
    summarize_period_profit,
)
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .periods import PROFIT_SUMMARY_QUERY_PARAMETERS, parse_profit_period
from .serializers import serialize_period_profit


class ProfitSummaryView(APIView):
    """Return one authorized store's explained estimated-profit period summary."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(
            request.query_params,
            PROFIT_SUMMARY_QUERY_PARAMETERS,
        )
        start_date, end_date = parse_profit_period(
            start_value=request.query_params.get("start_date"),
            end_value=request.query_params.get("end_date"),
        )
        store = require_authorized_store(request.user)
        try:
            summary = summarize_period_profit(
                store=store,
                start_date=start_date,
                end_date=end_date,
            )
        except (PeriodProfitAggregationError, OrderProfitCalculationError) as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        return Response(
            serialize_period_profit(summary, store_timezone=store.timezone)
        )
