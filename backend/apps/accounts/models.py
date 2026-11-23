"""Core account, store, and fixed staff-membership records."""
from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class UUIDTimeStampedModel(models.Model):
    """Shared server-owned identifiers and audit times for mutable records."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AccountManager(models.Manager):
    """Create password-backed accounts with one canonical email format."""

    def normalize_email(self, email: str) -> str:
        return BaseUserManager.normalize_email(email).strip().lower()

    def create_user(self, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not password:
            raise ValueError("A password is required.")
        account = self.model(email=self.normalize_email(email), **extra_fields)
        account.set_password(password)
        account.save(using=self._db)
        return account


class Account(UUIDTimeStampedModel):
    """Minimal password-authentication identity; never a seller-data super-role."""

    email = models.EmailField(max_length=254)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="accounts_account_email_ci_unique"
            )
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def clean(self):
        super().clean()
        self.email = Account.objects.normalize_email(self.email)
        if not self.email:
            raise ValidationError({"email": "An email address is required."})

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Store(UUIDTimeStampedModel):
    """One seller-owned tenant root for all future operational records."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_store",
    )
    name = models.CharField(max_length=160)
    timezone = models.CharField(max_length=64, default="Asia/Dhaka")
    currency_code = models.CharField(max_length=3, default="BDT")

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "A store name is required."})

        self.timezone = self.timezone.strip()
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValidationError({"timezone": "Use a valid IANA timezone."}) from None

        self.currency_code = self.currency_code.strip().upper()
        if self.currency_code != "BDT":
            raise ValidationError({"currency_code": "SellerOS uses BDT in this prototype."})

        if self.owner_id and StoreMembership.objects.filter(
            account_id=self.owner_id
        ).exists():
            raise ValidationError(
                {"owner": "A staff member cannot own a SellerOS store."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class StoreMembership(UUIDTimeStampedModel):
    """Fixed STAFF relation; owners are represented only by Store.owner."""

    class Role(models.TextChoices):
        STAFF = "STAFF", "Staff"

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="staff_memberships",
    )
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_membership",
    )
    role = models.CharField(max_length=16, choices=Role, default=Role.STAFF)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role="STAFF"),
                name="accounts_membership_role_staff_only",
            )
        ]

    def clean(self):
        super().clean()
        if self.role != self.Role.STAFF:
            raise ValidationError({"role": "Only the fixed STAFF role is allowed."})
        if self.account_id and Store.objects.filter(owner_id=self.account_id).exists():
            raise ValidationError(
                {"account": "A store owner cannot also hold a staff membership."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
