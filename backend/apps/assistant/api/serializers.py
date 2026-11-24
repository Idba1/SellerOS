"""Strict request validation for the customer-assistant draft endpoint."""
from rest_framework import serializers

from apps.assistant.retrieval import MAX_CUSTOMER_MESSAGE_LENGTH


class AssistantDraftRequestSerializer(serializers.Serializer):
    customer_message = serializers.CharField(
        max_length=MAX_CUSTOMER_MESSAGE_LENGTH,
        trim_whitespace=False,
    )

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

    def validate_customer_message(self, value):
        if not " ".join(value.split()):
            raise serializers.ValidationError("Customer message cannot be blank.")
        return value
