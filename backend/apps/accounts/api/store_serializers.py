"""Minimal store-profile representation and creation validation."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Store


class StoreProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ("id", "name", "timezone", "currency_code")
        read_only_fields = fields


class StoreCreateSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(max_length=64, required=False)

    class Meta:
        model = Store
        fields = ("name", "timezone")

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

    def validate_timezone(self, value):
        value = value.strip()
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise serializers.ValidationError("Use a valid IANA timezone.") from None
        return value

    def create(self, validated_data):
        try:
            return Store.objects.create(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
