"""Fail-closed draft-request API; no provider or external action is invoked."""
from __future__ import annotations

import time

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assistant.context import build_assistant_reply_context
from apps.assistant.evaluation import record_assistant_evaluation
from apps.assistant.models import AssistantEvaluationLog
from apps.assistant.retrieval import AssistantRetrievalError
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .serializers import AssistantDraftRequestSerializer


class AssistantDraftView(APIView):
    """Record safe request evidence and expose the current unavailable state."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant_draft"

    def post(self, request):
        validate_query_parameters(request.query_params, set())
        serializer = AssistantDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store = require_authorized_store(request.user)
        customer_message = serializer.validated_data["customer_message"]
        started_at = time.monotonic()
        try:
            context = build_assistant_reply_context(
                request.user,
                customer_message=customer_message,
            )
        except AssistantRetrievalError as error:
            raise ValidationError({"customer_message": [str(error)]}) from error

        if time.monotonic() - started_at > settings.ASSISTANT_CONTEXT_BUILD_MAX_SECONDS:
            record_assistant_evaluation(
                store=store,
                requested_by=request.user,
                customer_message_length=len(customer_message),
                context=context,
                outcome_state=AssistantEvaluationLog.OutcomeState.CONTEXT_TIMED_OUT,
                warning_codes=("context_build_timed_out",),
            )
            return self._unavailable_response("context_build_timed_out")

        record_assistant_evaluation(
            store=store,
            requested_by=request.user,
            customer_message_length=len(customer_message),
            context=context,
            outcome_state=AssistantEvaluationLog.OutcomeState.PROVIDER_UNAVAILABLE,
            warning_codes=("provider_execution_disabled",),
        )
        return self._unavailable_response("provider_execution_disabled")

    @staticmethod
    def _unavailable_response(warning: str) -> Response:
        return Response(
            {
                "error": {
                    "code": "assistant_unavailable",
                    "details": {
                        "detail": "Assistant generation is unavailable.",
                        "state": "unavailable",
                        "warnings": [warning],
                    },
                }
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
