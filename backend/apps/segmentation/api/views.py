"""Server-scoped read endpoint for one deterministic customer segment."""
from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.segmentation.features import CustomerFeatureError
from apps.segmentation.service import CustomerSegmentError, calculate_customer_segment
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .serializers import CustomerSegmentAssignmentSerializer


SEGMENT_QUERY_PARAMETERS = {"as_of"}


class CustomerSegmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        validate_query_parameters(request.query_params, SEGMENT_QUERY_PARAMETERS)
        store = require_authorized_store(request.user)
        customer = get_object_or_404(Customer.objects.filter(store=store), pk=customer_id)
        as_of = _parse_aware_as_of(request.query_params.get("as_of"))
        try:
            assignment = calculate_customer_segment(
                store=store,
                customer=customer,
                as_of=as_of,
            )
        except (CustomerFeatureError, CustomerSegmentError) as error:
            raise ValidationError({"as_of": [str(error)]}) from error
        return Response(CustomerSegmentAssignmentSerializer(assignment).data)


def _parse_aware_as_of(value: str | None) -> datetime:
    if value is None:
        raise ValidationError({"as_of": ["This query parameter is required."]})
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            {"as_of": ["Use an ISO 8601 timestamp with a timezone offset."]}
        ) from None
    if timezone.is_naive(parsed):
        raise ValidationError(
            {"as_of": ["Use an ISO 8601 timestamp with a timezone offset."]}
        )
    return parsed
