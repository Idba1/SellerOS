"""Store-scoped, read-only catalogue endpoints."""
from django.db.models.functions import Lower
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store, scope_to_authorized_store

from ..models import Product
from ..serializers import ProductDetailSerializer, ProductSerializer, ProductWriteSerializer


PRODUCT_LIST_QUERY_PARAMETERS = {
    "category",
    "is_active",
    "ordering",
    "page",
    "page_size",
}
PRODUCT_ORDERINGS = {"name", "-name", "created_at", "-created_at"}


def parse_boolean_query(value, field):
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValidationError({field: ["Use true or false."]})


def ordered_products(queryset, ordering):
    if ordering == "name":
        return queryset.order_by(Lower("name").asc(), "id")
    if ordering == "-name":
        return queryset.order_by(Lower("name").desc(), "-id")
    if ordering == "created_at":
        return queryset.order_by("created_at", "id")
    if ordering == "-created_at":
        return queryset.order_by("-created_at", "-id")
    raise ValidationError({"ordering": ["Unsupported ordering value."]})


class ProductListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, PRODUCT_LIST_QUERY_PARAMETERS)
        products = scope_to_authorized_store(Product.objects.all(), request.user)

        category = request.query_params.get("category")
        if category is not None:
            category = category.strip()
            if not category:
                raise ValidationError({"category": ["Use a non-blank category."]})
            products = products.filter(category__iexact=category)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            products = products.filter(
                is_active=parse_boolean_query(is_active, "is_active")
            )

        ordering = request.query_params.get("ordering", "name")
        if ordering not in PRODUCT_ORDERINGS:
            raise ValidationError({"ordering": ["Unsupported ordering value."]})
        products = ordered_products(products, ordering)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(products, request, view=self)
        return paginator.get_paginated_response(ProductSerializer(page, many=True).data)

    def post(self, request):
        store = require_authorized_store(request.user)
        serializer = ProductWriteSerializer(data=request.data, context={"store": store})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=201)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        validate_query_parameters(request.query_params, set())
        products = scope_to_authorized_store(
            Product.objects.prefetch_related("variants"), request.user
        )
        product = get_object_or_404(products, pk=product_id)
        return Response(ProductDetailSerializer(product).data)

    def patch(self, request, product_id):
        products = scope_to_authorized_store(Product.objects.all(), request.user)
        product = get_object_or_404(products, pk=product_id)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_product = serializer.save()
        return Response(ProductSerializer(updated_product).data)
