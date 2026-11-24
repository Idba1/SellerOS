"""Immutable, minimized evidence for customer-assistant evaluation requests."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Store, UUIDTimeStampedModel
from core.permissions import has_store_access


class AssistantEvaluationLog(UUIDTimeStampedModel):
    """Metadata-only evidence; never stores a message, prompt, draft, or secret."""

    class OutcomeState(models.TextChoices):
        PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE", "Provider unavailable"
        CONTEXT_TIMED_OUT = "CONTEXT_TIMED_OUT", "Context timed out"

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="assistant_evaluation_logs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assistant_evaluation_logs",
    )
    outcome_state = models.CharField(max_length=32, choices=OutcomeState.choices)
    provider_state = models.CharField(max_length=32, default="DISABLED")
    message_length = models.PositiveSmallIntegerField()
    contact_identifiers_redacted = models.BooleanField(default=False)
    context_fact_count = models.PositiveSmallIntegerField(default=0)
    source_metadata = models.JSONField(default=list, blank=True)
    warning_codes = models.JSONField(default=list)

    class Meta:
        indexes = [
            models.Index(
                fields=("store", "created_at"),
                name="asst_eval_store_created_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.store_id and self.requested_by_id and not has_store_access(
            self.requested_by, self.store
        ):
            raise ValidationError(
                {"requested_by": "Requester must have active store access."}
            )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                {"non_field_errors": ["Assistant evaluation logs are immutable."]}
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            {"non_field_errors": ["Assistant evaluation logs cannot be deleted."]}
        )
