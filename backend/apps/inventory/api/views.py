"""Store-scoped stock balances, movement history, and manual adjustments."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.functions import Lower
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import InventoryMovement, StockUnit
from apps.inventory.services import apply_stock_adjustment
from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters
from core.permissions import scope_to_authorized_store

from .serializers import (
    InventoryMovementSerializer,
    ManualStockAdjustmentSerializer,
    StockUnitSerializer,
)


PAGINATION_QUERY_PARAMETERS = {"page", "page_size"}


def get_store_stock_unit_or_404(account, stock_unit_id):
    """Look up a unit only inside the authenticated account's current store."""

    stock_units = scope_to_authorized_store(
        StockUnit.objects.select_related("product", "variant"), account
    )
    return get_object_or_404(stock_units, pk=stock_unit_id)


class InventoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, PAGINATION_QUERY_PARAMETERS)
        stock_units = scope_to_authorized_store(
            StockUnit.objects.select_related("product", "variant"), request.user
        ).order_by(Lower("product__name").asc(), "id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(stock_units, request, view=self)
        return paginator.get_paginated_response(StockUnitSerializer(page, many=True).data)


class InventoryMovementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, stock_unit_id):
        validate_query_parameters(request.query_params, PAGINATION_QUERY_PARAMETERS)
        stock_unit = get_store_stock_unit_or_404(request.user, stock_unit_id)
        movements = stock_unit.movements.order_by("-occurred_at", "-id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(movements, request, view=self)
        return paginator.get_paginated_response(
            InventoryMovementSerializer(page, many=True).data
        )


class ManualStockAdjustmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, stock_unit_id):
        validate_query_parameters(request.query_params, set())
        stock_unit = get_store_stock_unit_or_404(request.user, stock_unit_id)
        serializer = ManualStockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement = apply_stock_adjustment(
                stock_unit_id=stock_unit.pk,
                movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                quantity_delta=serializer.validated_data["quantity_delta"],
                reason=serializer.validated_data["reason"],
                created_by=request.user,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict) from error

        return Response(
            InventoryMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )
