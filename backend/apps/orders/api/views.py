"""Authenticated, store-scoped order list and detail reads."""
from datetime import date

from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import SalesOrder
from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters
from core.permissions import scope_to_authorized_store

from .serializers import OrderDetailSerializer, OrderSerializer


ORDER_LIST_QUERY_PARAMETERS = {"status", "created_from", "created_to", "page", "page_size"}
ORDER_STATUSES = {choice for choice, _ in SalesOrder.Status.choices}


def parse_iso_date(value, field):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({field: ["Use an ISO date in YYYY-MM-DD format."]}) from None


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, ORDER_LIST_QUERY_PARAMETERS)
        orders = scope_to_authorized_store(
            SalesOrder.objects.select_related("customer"), request.user
        )

        status = request.query_params.get("status")
        if status is not None:
            if status not in ORDER_STATUSES:
                raise ValidationError({"status": ["Unsupported order status."]})
            orders = orders.filter(status=status)

        created_from = request.query_params.get("created_from")
        created_to = request.query_params.get("created_to")
        start_date = parse_iso_date(created_from, "created_from") if created_from else None
        end_date = parse_iso_date(created_to, "created_to") if created_to else None
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                {"created_to": ["Use a date on or after created_from."]}
            )
        if start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        orders = orders.order_by("-created_at", "-id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request, view=self)
        return paginator.get_paginated_response(OrderSerializer(page, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        validate_query_parameters(request.query_params, set())
        orders = scope_to_authorized_store(
            SalesOrder.objects.select_related("customer").prefetch_related("items"),
            request.user,
        )
        order = get_object_or_404(orders, pk=order_id)
        return Response(OrderDetailSerializer(order).data)
