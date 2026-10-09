from rest_framework.exceptions import ValidationError


def validate_query_parameters(query, allowed):
    """Endpoint supplies an explicit allowlist before filtering its scoped queryset."""
    errors = {}
    for name in query:
        if name not in allowed:
            errors[name] = ["Unsupported query parameter."]
        elif len(query.getlist(name)) != 1:
            errors[name] = ["Supply this parameter once."]
    if errors:
        raise ValidationError(errors)
