"""Strict seller-facing expense representations."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Account, Store
from apps.expenses.models import Expense


class StrictExpensePayloadSerializer(serializers.ModelSerializer):
    """Reject server-owned and unknown fields instead of ignoring them."""

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


class ExpenseSerializer(serializers.ModelSerializer):
    """Store ownership and recorder identity remain server-owned."""

    class Meta:
        model = Expense
        fields = (
            "id",
            "description",
            "category",
            "amount",
            "incurred_on",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ExpenseWriteSerializer(StrictExpensePayloadSerializer):
    """Validate the editable fields while preserving ownership and recorder facts."""

    class Meta:
        model = Expense
        fields = ("description", "category", "amount", "incurred_on")

    def create(self, validated_data):
        store = self.context.get("store")
        recorded_by = self.context.get("recorded_by")
        if not isinstance(store, Store) or not isinstance(recorded_by, Account):
            raise serializers.ValidationError(
                {"non_field_errors": ["Server store context is required."]}
            )
        try:
            return Expense.objects.create(
                store=store,
                recorded_by=recorded_by,
                **validated_data,
            )
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
