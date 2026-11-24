"""Shared explicit timestamp-range parsing for analytics read endpoints."""
from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError


ANALYTICS_PERIOD_QUERY_PARAMETERS = {"period_start", "period_end"}


def parse_aware_timestamp(value, field):
    if value is None:
        raise ValidationError({field: ["This query parameter is required."]})
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            {field: ["Use an ISO 8601 timestamp with a timezone offset."]}
        ) from None
    if timezone.is_naive(parsed):
        raise ValidationError(
            {field: ["Use an ISO 8601 timestamp with a timezone offset."]}
        )
    return parsed
