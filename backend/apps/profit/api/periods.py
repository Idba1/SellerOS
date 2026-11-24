"""Strict whole-day period parsing for the profit summary endpoint."""
from datetime import date

from rest_framework.exceptions import ValidationError


PROFIT_SUMMARY_QUERY_PARAMETERS = {"start_date", "end_date"}
MAX_PROFIT_PERIOD_DAYS = 366


def parse_profit_period(*, start_value, end_value) -> tuple[date, date]:
    """Return an inclusive date range with a bounded, explicit request span."""

    start_date = _parse_date(start_value, "start_date")
    end_date = _parse_date(end_value, "end_date")
    if end_date < start_date:
        raise ValidationError(
            {"non_field_errors": ["End date cannot precede start date."]}
        )
    if (end_date - start_date).days + 1 > MAX_PROFIT_PERIOD_DAYS:
        raise ValidationError(
            {
                "non_field_errors": [
                    f"A profit period cannot exceed {MAX_PROFIT_PERIOD_DAYS} days."
                ]
            }
        )
    return start_date, end_date


def _parse_date(value, field_name) -> date:
    if value is None:
        raise ValidationError({field_name: ["This query parameter is required."]})
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            {field_name: ["Use an ISO 8601 date (YYYY-MM-DD)."]}
        ) from None
