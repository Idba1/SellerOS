"""Store-owned operating expenses for later deterministic profit analysis."""
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.accounts.models import Store, StoreMembership, UUIDTimeStampedModel


class Expense(UUIDTimeStampedModel):
    """One seller-entered general operating expense, recorded in the store's BDT scope."""

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    description = models.CharField(max_length=240)
    category = models.CharField(max_length=80)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    incurred_on = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_expenses",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="expenses_expense_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.category}: {self.amount}"

    def clean(self):
        super().clean()
        if isinstance(self.description, str):
            self.description = self.description.strip()
        if isinstance(self.category, str):
            self.category = self.category.strip()
        if not self.description:
            raise ValidationError({"description": "An expense description is required."})
        if not self.category:
            raise ValidationError({"category": "An expense category is required."})
        if self.incurred_on and self.incurred_on > self._store_local_today():
            raise ValidationError(
                {"incurred_on": "An expense cannot be dated in the future."}
            )
        if self.store_id and self.recorded_by_id:
            is_owner = self.store.owner_id == self.recorded_by_id
            is_active_staff = StoreMembership.objects.filter(
                store_id=self.store_id,
                account_id=self.recorded_by_id,
                is_active=True,
            ).exists()
            if not is_owner and not is_active_staff:
                raise ValidationError(
                    {"recorded_by": "Recorder must have active store access."}
                )

    def _store_local_today(self):
        if self.store_id:
            return timezone.localdate(timezone=ZoneInfo(self.store.timezone))
        return timezone.localdate()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
