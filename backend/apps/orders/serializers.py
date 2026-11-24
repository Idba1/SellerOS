"""Strict server-priced order-creation validation."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Store
from apps.catalog.models import Product, ProductVariant
from apps.customers.models import Customer

from .models import OrderItem, SalesOrder


MONEY_QUANTUM = Decimal("0.01")


class StrictPayloadSerializer(serializers.Serializer):
    """Reject any field that is not explicitly part of the create contract."""

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


class OrderItemCreateSerializer(StrictPayloadSerializer):
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(StrictPayloadSerializer):
    """Create one submitted order with server-derived catalogue snapshots."""

    customer_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    items = OrderItemCreateSerializer(many=True, min_length=1)
    order_discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    seller_delivery_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
        min_value=Decimal("0.00"),
    )

    def validate(self, attrs):
        store = self.context.get("store")
        if not isinstance(store, Store):
            raise serializers.ValidationError(
                {"non_field_errors": ["Server store context is required."]}
            )

        customer = self._resolve_customer(store, attrs["customer_id"])
        resolved_items, item_errors, line_grosses = self._resolve_items(
            store, attrs["items"]
        )
        if item_errors:
            raise serializers.ValidationError({"items": item_errors})

        order_gross = sum(line_grosses, Decimal("0.00"))
        if attrs["order_discount"] > order_gross:
            raise serializers.ValidationError(
                {"order_discount": ["Discount cannot exceed the order gross."]}
            )

        attrs["resolved_customer"] = customer
        attrs["resolved_items"] = resolved_items
        return attrs

    def create(self, validated_data):
        store = self.context["store"]
        customer = validated_data.pop("resolved_customer")
        resolved_items = validated_data.pop("resolved_items")
        validated_data.pop("customer_id")
        validated_data.pop("items")
        discount_allocations = allocate_discount(
            [item["line_gross"] for item in resolved_items],
            validated_data["order_discount"],
        )

        with transaction.atomic():
            order = SalesOrder.objects.create(
                store=store,
                customer=customer,
                status=SalesOrder.Status.PENDING,
                **validated_data,
            )
            for item, discount_allocation in zip(resolved_items, discount_allocations):
                product = item["product"]
                variant = item["variant"]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    product_name_snapshot=product.name,
                    variant_name_snapshot=variant.name if variant is not None else None,
                    quantity=item["quantity"],
                    selling_price_snapshot=product.selling_price,
                    unit_cost_snapshot=None,
                    discount_allocation=discount_allocation,
                )
        return order

    @staticmethod
    def _resolve_customer(store, customer_id):
        if customer_id is None:
            return None
        try:
            return Customer.objects.get(pk=customer_id, store=store)
        except Customer.DoesNotExist as error:
            raise serializers.ValidationError(
                {"customer_id": ["Customer is not available in this store."]}
            ) from error

    @staticmethod
    def _resolve_items(store, raw_items):
        resolved_items = []
        item_errors = {}
        line_grosses = []
        for index, item in enumerate(raw_items):
            errors = {}
            product = Product.objects.filter(pk=item["product_id"], store=store).first()
            if product is None:
                errors["product_id"] = ["Product is not available in this store."]
            elif not product.is_active:
                errors["product_id"] = ["Product must be active for a new order."]

            variant = None
            variant_id = item["variant_id"]
            if product is not None and product.has_variants:
                if variant_id is None:
                    errors["variant_id"] = ["A variant is required for this product."]
                else:
                    variant = ProductVariant.objects.filter(
                        pk=variant_id, product=product
                    ).first()
                    if variant is None:
                        errors["variant_id"] = [
                            "Variant is not available for this product."
                        ]
                    elif not variant.is_active:
                        errors["variant_id"] = [
                            "Variant must be active for a new order."
                        ]
            elif product is not None and variant_id is not None:
                errors["variant_id"] = [
                    "Standalone products cannot use a variant."
                ]

            if errors:
                item_errors[index] = errors
                continue

            line_gross = product.selling_price * item["quantity"]
            resolved_items.append(
                {
                    "product": product,
                    "variant": variant,
                    "quantity": item["quantity"],
                    "line_gross": line_gross,
                }
            )
            line_grosses.append(line_gross)
        return resolved_items, item_errors, line_grosses


def allocate_discount(line_grosses: list[Decimal], order_discount: Decimal) -> list[Decimal]:
    """Allocate discount proportionally with a final-line remainder safeguard."""

    if not line_grosses:
        return []
    if order_discount == Decimal("0.00"):
        return [Decimal("0.00")] * len(line_grosses)

    order_gross = sum(line_grosses, Decimal("0.00"))
    allocations = []
    remaining_discount = order_discount
    for line_gross in line_grosses[:-1]:
        allocation = (order_discount * line_gross / order_gross).quantize(
            MONEY_QUANTUM, rounding=ROUND_HALF_UP
        )
        allocations.append(allocation)
        remaining_discount -= allocation
    allocations.append(remaining_discount)
    return allocations
