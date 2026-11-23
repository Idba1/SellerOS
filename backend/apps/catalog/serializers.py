"""Catalogue serializers with strict client payloads and server-owned relations."""
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Store

from .models import Product, ProductVariant


class StrictPayloadModelSerializer(serializers.ModelSerializer):
    """Reject ownership/relationship fields that are not part of a write contract."""

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


class ProductSerializer(serializers.ModelSerializer):
    """Read-only product representation; store ownership stays implicit in the API."""

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "category",
            "selling_price",
            "unit_cost",
            "has_variants",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductWriteSerializer(StrictPayloadModelSerializer):
    """Validate client-editable product fields without accepting a store selector."""

    category = serializers.CharField(
        max_length=80, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "category",
            "selling_price",
            "unit_cost",
            "has_variants",
            "is_active",
        )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A product name is required.")
        return value

    def validate_category(self, value):
        if value is None:
            return None
        return value.strip() or None

    def validate_selling_price(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Use a selling price greater than 0.00.")
        return value

    def validate_unit_cost(self, value):
        if value is not None and value < Decimal("0.00"):
            raise serializers.ValidationError("Use a nonnegative unit cost or omit it.")
        return value

    def create(self, validated_data):
        store = self.context.get("store")
        if not isinstance(store, Store):
            raise serializers.ValidationError(
                {"non_field_errors": ["Server store context is required."]}
            )
        try:
            return Product.objects.create(store=store, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return instance


class ProductVariantSerializer(serializers.ModelSerializer):
    """Read-only variant representation with its parent product identifier."""

    product_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "product_id", "name", "is_active", "created_at", "updated_at")
        read_only_fields = fields


class ProductDetailSerializer(ProductSerializer):
    """A product read with only its own store-inherited variants."""

    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ("variants",)
        read_only_fields = fields


class ProductVariantWriteSerializer(StrictPayloadModelSerializer):
    """Validate named variants against a server-resolved variant-based product."""

    class Meta:
        model = ProductVariant
        fields = ("name", "is_active")

    def get_product(self):
        product = self.context.get("product")
        if self.instance is not None and product is None:
            product = self.instance.product
        return product

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A variant name is required.")

        product = self.get_product()
        if isinstance(product, Product):
            duplicates = ProductVariant.objects.filter(
                product=product, name__iexact=value
            )
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    "A variant with this name already exists for the product."
                )
        return value

    def validate(self, attrs):
        product = self.get_product()
        if not isinstance(product, Product):
            raise serializers.ValidationError(
                {"non_field_errors": ["Server product context is required."]}
            )
        if self.instance is not None and product.pk != self.instance.product_id:
            raise serializers.ValidationError(
                {"product": ["A variant cannot be moved to another product."]}
            )
        if not product.has_variants:
            raise serializers.ValidationError(
                {"product": ["Variants require has_variants=True."]}
            )
        return attrs

    def create(self, validated_data):
        product = self.get_product()
        try:
            return ProductVariant.objects.create(product=product, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return instance
