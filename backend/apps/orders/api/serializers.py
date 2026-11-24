"""Read-only order representations for seller review."""
from rest_framework import serializers

from apps.orders.models import OrderItem, SalesOrder


class OrderItemReadSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(read_only=True)
    variant_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "variant_id",
            "product_name_snapshot",
            "variant_name_snapshot",
            "quantity",
            "selling_price_snapshot",
            "unit_cost_snapshot",
            "discount_allocation",
            "created_at",
        )
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(read_only=True, allow_null=True)
    customer_display_name = serializers.CharField(
        source="customer.display_name", read_only=True, allow_null=True
    )

    class Meta:
        model = SalesOrder
        fields = (
            "id",
            "customer_id",
            "customer_display_name",
            "status",
            "currency_code",
            "order_discount",
            "seller_delivery_cost",
            "confirmed_at",
            "delivered_at",
            "cancelled_at",
            "return_requested_at",
            "returned_at",
            "refunded_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderDetailSerializer(OrderSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ("items",)
        read_only_fields = fields
