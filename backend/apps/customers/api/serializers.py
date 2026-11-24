"""Customer representations with server-owned store context."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Store
from apps.customers.models import Customer


class StrictCustomerPayloadSerializer(serializers.ModelSerializer):
    """Reject client fields outside the customer write contract."""

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


class CustomerSerializer(serializers.ModelSerializer):
    """Seller-visible profile data; store ownership is implicit."""

    class Meta:
        model = Customer
        fields = (
            "id",
            "display_name",
            "phone",
            "email",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CustomerWriteSerializer(StrictCustomerPayloadSerializer):
    """Validate only seller-editable customer fields."""

    phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True, allow_null=True
    )
    email = serializers.EmailField(
        max_length=254, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Customer
        fields = ("display_name", "phone", "email")

    def validate_display_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A customer name is required.")
        return value

    def validate_phone(self, value):
        if value is None:
            return None
        return value.strip() or None

    def validate_email(self, value):
        if value is None:
            return None
        return value.strip() or None

    def create(self, validated_data):
        store = self.context.get("store")
        if not isinstance(store, Store):
            raise serializers.ValidationError(
                {"non_field_errors": ["Server store context is required."]}
            )
        try:
            return Customer.objects.create(store=store, **validated_data)
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
