"""Authenticated, store-scoped expense reads and maintenance writes."""
from datetime import date

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.models import Expense
from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store, scope_to_authorized_store

from .serializers import ExpenseSerializer, ExpenseWriteSerializer


EXPENSE_LIST_QUERY_PARAMETERS = {
    "category",
    "incurred_from",
    "incurred_to",
    "page",
    "page_size",
}


def parse_iso_date(value, field):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({field: ["Use an ISO date in YYYY-MM-DD format."]}) from None


class ExpenseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, EXPENSE_LIST_QUERY_PARAMETERS)
        expenses = scope_to_authorized_store(Expense.objects.all(), request.user)

        category = request.query_params.get("category")
        if category is not None:
            category = category.strip()
            if not category:
                raise ValidationError({"category": ["Use a non-blank category."]})
            expenses = expenses.filter(category__iexact=category)

        incurred_from = request.query_params.get("incurred_from")
        incurred_to = request.query_params.get("incurred_to")
        start_date = (
            parse_iso_date(incurred_from, "incurred_from") if incurred_from else None
        )
        end_date = (
            parse_iso_date(incurred_to, "incurred_to") if incurred_to else None
        )
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                {"incurred_to": ["Use a date on or after incurred_from."]}
            )
        if start_date:
            expenses = expenses.filter(incurred_on__gte=start_date)
        if end_date:
            expenses = expenses.filter(incurred_on__lte=end_date)
        expenses = expenses.order_by("-incurred_on", "-created_at", "-id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(expenses, request, view=self)
        return paginator.get_paginated_response(ExpenseSerializer(page, many=True).data)

    def post(self, request):
        validate_query_parameters(request.query_params, set())
        store = require_authorized_store(request.user)
        serializer = ExpenseWriteSerializer(
            data=request.data,
            context={"store": store, "recorded_by": request.user},
        )
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, account, expense_id):
        expenses = scope_to_authorized_store(Expense.objects.all(), account)
        return get_object_or_404(expenses, pk=expense_id)

    def get(self, request, expense_id):
        validate_query_parameters(request.query_params, set())
        return Response(ExpenseSerializer(self.get_object(request.user, expense_id)).data)

    def patch(self, request, expense_id):
        validate_query_parameters(request.query_params, set())
        expense = self.get_object(request.user, expense_id)
        serializer = ExpenseWriteSerializer(expense, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_expense = serializer.save()
        return Response(ExpenseSerializer(updated_expense).data)
