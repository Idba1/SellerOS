"""Minimal store-owned customer profiles without sensitive profiling fields."""
from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Store, UUIDTimeStampedModel


class Customer(UUIDTimeStampedModel):
    """A seller-entered customer label and optional direct contact details."""

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="customers",
    )
    display_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32, null=True, blank=True, default=None)
    email = models.EmailField(max_length=254, null=True, blank=True, default=None)

    def __str__(self):
        return self.display_name

    def normalize_fields(self):
        """Normalize optional seller-entered contact values before validation."""

        if isinstance(self.display_name, str):
            self.display_name = self.display_name.strip()
        if isinstance(self.phone, str):
            self.phone = self.phone.strip() or None
        if isinstance(self.email, str):
            self.email = BaseUserManager.normalize_email(self.email.strip()) or None

    def clean(self):
        super().clean()
        self.normalize_fields()
        if not self.display_name:
            raise ValidationError({"display_name": "A customer name is required."})

    def save(self, *args, **kwargs):
        self.normalize_fields()
        self.full_clean()
        return super().save(*args, **kwargs)
