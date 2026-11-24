"""Transactional inventory operations for the cached-balance ledger."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventory.models import InventoryMovement, StockUnit

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


class StockAdjustmentError(ValidationError):
    """Raised when a requested adjustment cannot safely be applied."""


def apply_stock_adjustment(
    *,
    stock_unit_id: uuid.UUID,
    movement_type: str,
    quantity_delta: int,
    created_by: AbstractBaseUser,
    operation_id: uuid.UUID | str | None = None,
    reason: str | None = None,
    reversal_of: InventoryMovement | None = None,
) -> InventoryMovement:
    """Atomically append a valid movement and update its cached balance.

    Callers must already have obtained ``stock_unit_id`` through an authorized
    store-scoped workflow. The movement model independently verifies that the
    creator has access to that stock unit's store.
    """

    if isinstance(quantity_delta, bool) or not isinstance(quantity_delta, int):
        raise StockAdjustmentError(
            {"quantity_delta": ["Quantity delta must be a whole number."]}
        )

    resolved_operation_id = _normalize_operation_id(operation_id)

    with transaction.atomic():
        try:
            stock_unit = (
                StockUnit.objects.select_for_update(of=("self",))
                .select_related("store", "product", "variant")
                .get(pk=stock_unit_id)
            )
        except StockUnit.DoesNotExist as error:
            raise StockAdjustmentError(
                {"stock_unit": ["Stock unit was not found."]}
            ) from error

        if InventoryMovement.objects.filter(
            stock_unit=stock_unit,
            movement_type=movement_type,
            operation_id=resolved_operation_id,
        ).exists():
            raise StockAdjustmentError(
                {"operation_id": ["This stock operation was already applied."]}
            )

        resulting_quantity = stock_unit.quantity_on_hand + quantity_delta
        if resulting_quantity < 0:
            raise StockAdjustmentError(
                {
                    "quantity_delta": [
                        "This adjustment would make stock quantity negative."
                    ]
                }
            )

        movement = InventoryMovement(
            store=stock_unit.store,
            stock_unit=stock_unit,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            operation_id=resolved_operation_id,
            reason=reason,
            created_by=created_by,
            reversal_of=reversal_of,
        )
        movement.save()

        stock_unit.quantity_on_hand = resulting_quantity
        stock_unit.save(update_fields={"quantity_on_hand", "updated_at"})

    return movement


def _normalize_operation_id(operation_id: uuid.UUID | str | None) -> uuid.UUID:
    """Return a UUID operation identifier without accepting malformed values."""

    if operation_id is None:
        return uuid.uuid4()

    try:
        return uuid.UUID(str(operation_id))
    except (TypeError, ValueError, AttributeError) as error:
        raise StockAdjustmentError(
            {"operation_id": ["Operation ID must be a UUID."]}
        ) from error
