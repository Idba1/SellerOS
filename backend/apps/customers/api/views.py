"""Store-scoped customer list, detail, create, and update endpoints."""
from django.db.models.functions import Lower
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store, scope_to_authorized_store

from .serializers import CustomerSerializer, CustomerWriteSerializer


PAGINATION_QUERY_PARAMETERS = {"page", "page_size"}


class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, PAGINATION_QUERY_PARAMETERS)
        customers = scope_to_authorized_store(Customer.objects.all(), request.user)
        customers = customers.order_by(Lower("display_name").asc(), "id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(customers, request, view=self)
        return paginator.get_paginated_response(CustomerSerializer(page, many=True).data)

    def post(self, request):
        validate_query_parameters(request.query_params, set())
        store = require_authorized_store(request.user)
        serializer = CustomerWriteSerializer(data=request.data, context={"store": store})
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        validate_query_parameters(request.query_params, set())
        customers = scope_to_authorized_store(Customer.objects.all(), request.user)
        customer = get_object_or_404(customers, pk=customer_id)
        return Response(CustomerSerializer(customer).data)

    def patch(self, request, customer_id):
        validate_query_parameters(request.query_params, set())
        customers = scope_to_authorized_store(Customer.objects.all(), request.user)
        customer = get_object_or_404(customers, pk=customer_id)
        serializer = CustomerWriteSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_customer = serializer.save()
        return Response(CustomerSerializer(updated_customer).data)
