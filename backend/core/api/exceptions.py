"""Wrap DRF-handled errors while retaining status, headers and nested details."""
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unexpected failures follow Django's error handling; never serialize exc.
        return None
    code = "validation_error" if isinstance(exc, ValidationError) else getattr(
        exc, "default_code", "api_error"
    )
    if response.status_code == 404:
        code = "not_found"
    response.data = {"error": {"code": code, "details": response.data}}
    return response
