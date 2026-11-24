"""Store-owned cached stock balances and their immutable movement evidence."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Store, StoreMembership, UUIDTimeStampedModel
from apps.catalog.models import Product, ProductVariant


class StockUnit(UUIDTimeStampedModel):
    """One cached stock balance for a standalone product or one product variant."""

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="stock_units",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_units",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="stock_units",
        null=True,
        blank=True,
        default=None,
    )
    quantity_on_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=models.Q(variant__isnull=True),
                name="inventory_stock_unit_standalone_product_unique",
            ),
            models.UniqueConstraint(
                fields=("variant",),
                condition=models.Q(variant__isnull=False),
                name="inventory_stock_unit_variant_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_on_hand__gte=0),
                name="inventory_stock_unit_quantity_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(low_stock_threshold__gte=0)
                | models.Q(low_stock_threshold__isnull=True),
                name="inventory_stock_unit_threshold_nonnegative_or_null",
            ),
        ]

    def __str__(self):
        return f"{self.product} stock"

    @property
    def is_low_stock(self):
        """A threshold is seller-configured; a missing threshold is not low stock."""

        return (
            self.low_stock_threshold is not None
            and self.quantity_on_hand <= self.low_stock_threshold
        )

    def clean(self):
        super().clean()
        if self.product_id and self.store_id and self.product.store_id != self.store_id:
            raise ValidationError({"store": "Stock unit store must match its product."})

        if self.variant_id:
            if not self.product.has_variants:
                raise ValidationError(
                    {"variant": "Standalone products cannot have a stock variant."}
                )
            if self.variant.product_id != self.product_id:
                raise ValidationError(
                    {"variant": "Variant must belong to the selected product."}
                )
        elif self.product_id and self.product.has_variants:
            raise ValidationError(
                {"variant": "Variant-based products require a variant stock unit."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class InventoryMovement(UUIDTimeStampedModel):
    """An immutable nonzero stock change; balance updates are a later service concern."""

    class MovementType(models.TextChoices):
        OPENING_BALANCE = "OPENING_BALANCE", "Opening balance"
        MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", "Manual adjustment"
        ORDER_CONFIRMATION_DEDUCTION = (
            "ORDER_CONFIRMATION_DEDUCTION",
            "Order confirmation deduction",
        )
        ORDER_CANCELLATION_RESTORATION = (
            "ORDER_CANCELLATION_RESTORATION",
            "Order cancellation restoration",
        )
        ORDER_RETURN_RESTORATION = (
            "ORDER_RETURN_RESTORATION",
            "Order return restoration",
        )

    RESTORATION_TYPES = {
        MovementType.ORDER_CANCELLATION_RESTORATION,
        MovementType.ORDER_RETURN_RESTORATION,
    }

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    stock_unit = models.ForeignKey(
        StockUnit,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=32, choices=MovementType.choices)
    quantity_delta = models.IntegerField()
    operation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    reason = models.CharField(max_length=240, null=True, blank=True, default=None)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="reversal_movement",
        null=True,
        blank=True,
        default=None,
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="inventory_movement_quantity_delta_nonzero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        movement_type="OPENING_BALANCE", quantity_delta__gt=0
                    )
                    | models.Q(movement_type="MANUAL_ADJUSTMENT")
                    | models.Q(
                        movement_type="ORDER_CONFIRMATION_DEDUCTION",
                        quantity_delta__lt=0,
                    )
                    | models.Q(
                        movement_type="ORDER_CANCELLATION_RESTORATION",
                        quantity_delta__gt=0,
                    )
                    | models.Q(
                        movement_type="ORDER_RETURN_RESTORATION",
                        quantity_delta__gt=0,
                    )
                ),
                name="inventory_movement_type_delta_direction",
            ),
            models.UniqueConstraint(
                fields=("stock_unit", "movement_type", "operation_id"),
                name="inventory_movement_stock_type_operation_unique",
            ),
        ]

    def __str__(self):
        return f"{self.movement_type}: {self.quantity_delta}"

    def clean(self):
        super().clean()
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        if self.movement_type == self.MovementType.MANUAL_ADJUSTMENT and not self.reason:
            raise ValidationError(
                {"reason": "A manual adjustment requires a reason."}
            )

        if self.stock_unit_id and self.store_id and self.stock_unit.store_id != self.store_id:
            raise ValidationError(
                {"stock_unit": "Movement store must match its stock unit."}
            )

        if self.created_by_id and self.store_id:
            is_owner = self.store.owner_id == self.created_by_id
            is_active_staff = StoreMembership.objects.filter(
                store_id=self.store_id,
                account_id=self.created_by_id,
                is_active=True,
            ).exists()
            if not is_owner and not is_active_staff:
                raise ValidationError(
                    {"created_by": "Movement creator must have active store access."}
                )

        is_restoration = self.movement_type in self.RESTORATION_TYPES
        if is_restoration and not self.reversal_of_id:
            raise ValidationError(
                {"reversal_of": "Restoration movements require the original deduction."}
            )
        if not is_restoration and self.reversal_of_id:
            raise ValidationError(
                {"reversal_of": "Only restoration movements can reference a deduction."}
            )
        if self.reversal_of_id:
            if self.reversal_of.store_id != self.store_id:
                raise ValidationError(
                    {"reversal_of": "Original movement must belong to the same store."}
                )
            if self.reversal_of.stock_unit_id != self.stock_unit_id:
                raise ValidationError(
                    {"reversal_of": "Original movement must use the same stock unit."}
                )
            if (
                self.reversal_of.movement_type
                != self.MovementType.ORDER_CONFIRMATION_DEDUCTION
            ):
                raise ValidationError(
                    {"reversal_of": "Only a confirmation deduction can be restored."}
                )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                {"non_field_errors": ["Inventory movements are immutable."]}
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            {"non_field_errors": ["Inventory movements cannot be deleted."]}
        )
