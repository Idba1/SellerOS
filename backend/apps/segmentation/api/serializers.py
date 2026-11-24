"""Stable read-only serializer for evidence-bound customer segment responses."""
from rest_framework import serializers

from apps.segmentation.service import CustomerSegmentAssignment


class CustomerSegmentValuesSerializer(serializers.Serializer):
    recorded_purchase_count = serializers.IntegerField(read_only=True)
    last_recorded_purchase_at = serializers.DateTimeField(read_only=True, allow_null=True)
    recency_days = serializers.IntegerField(read_only=True, allow_null=True)
    trailing_365_day_spend_bdt = serializers.DecimalField(
        read_only=True,
        max_digits=12,
        decimal_places=2,
    )


class CustomerSegmentAssignmentSerializer(serializers.Serializer):
    segment = serializers.SerializerMethodField()
    rule_version = serializers.CharField(read_only=True)
    as_of = serializers.DateTimeField(source="features.as_of", read_only=True)
    store_timezone = serializers.CharField(
        source="features.store_timezone", read_only=True
    )
    values = serializers.SerializerMethodField()
    explanation = serializers.CharField(read_only=True)

    def get_segment(self, assignment: CustomerSegmentAssignment):
        return assignment.segment.value

    def get_values(self, assignment: CustomerSegmentAssignment):
        features = assignment.features
        return CustomerSegmentValuesSerializer(
            {
                "recorded_purchase_count": features.recorded_purchase_count,
                "last_recorded_purchase_at": features.last_recorded_purchase_at,
                "recency_days": features.recency_days,
                "trailing_365_day_spend_bdt": features.trailing_365_day_spend_bdt,
            }
        ).data
