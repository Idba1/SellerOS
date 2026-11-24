"""Read and manual-adjustment serializers for store-scoped inventory."""
from rest_framework import serializers

from apps.inventory.models import InventoryMovement, StockUnit


class StrictPayloadSerializer(serializers.Serializer):
    """Reject fields outside this endpoint's explicit write contract."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected = set(data.keys()) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {
                        field: ["This field is not allowed."]
                        for field in sorted(unexpected)
                    }
                )
        return super().to_internal_value(data)


class StockUnitSerializer(serializers.ModelSerializer):
    """Current seller-visible balance without a tenant selector."""

    product_id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    variant_id = serializers.UUIDField(read_only=True, allow_null=True)
    variant_name = serializers.CharField(
        source="variant.name", read_only=True, allow_null=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockUnit
        fields = (
            "id",
            "product_id",
            "product_name",
            "variant_id",
            "variant_name",
            "quantity_on_hand",
            "low_stock_threshold",
            "is_low_stock",
            "updated_at",
        )
        read_only_fields = fields


class InventoryMovementSerializer(serializers.ModelSerializer):
    """Auditable movement history without editable ownership data."""

    stock_unit_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)
    reversal_of_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = InventoryMovement
        fields = (
            "id",
            "stock_unit_id",
            "movement_type",
            "quantity_delta",
            "reason",
            "created_by_id",
            "reversal_of_id",
            "occurred_at",
        )
        read_only_fields = fields


class ManualStockAdjustmentSerializer(StrictPayloadSerializer):
    """The sole client-controlled inventory write payload in INV-03."""

    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=240, allow_blank=True, trim_whitespace=True)

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Use a nonzero quantity adjustment.")
        return value

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A manual adjustment requires a reason.")
        return value
