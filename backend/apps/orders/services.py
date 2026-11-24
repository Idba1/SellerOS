"""Atomic submitted-order confirmation and inventory deduction."""
import uuid
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import InventoryMovement, StockUnit
from apps.inventory.services import apply_stock_adjustment
from core.permissions import has_store_access

from .models import OrderStatusEvent, SalesOrder


class OrderConfirmationError(ValidationError):
    """Raised when a submitted order cannot atomically become confirmed."""


class OrderTransitionError(ValidationError):
    """Raised when a requested status transition is not safe to apply."""


SAFE_NO_EFFECT_TRANSITIONS = {
    (SalesOrder.Status.DRAFT, SalesOrder.Status.PENDING),
    (SalesOrder.Status.DRAFT, SalesOrder.Status.CANCELLED),
    (SalesOrder.Status.PENDING, SalesOrder.Status.CANCELLED),
    (SalesOrder.Status.CONFIRMED, SalesOrder.Status.PROCESSING),
    (SalesOrder.Status.PROCESSING, SalesOrder.Status.SHIPPED),
    (SalesOrder.Status.SHIPPED, SalesOrder.Status.DELIVERED),
    (SalesOrder.Status.DELIVERED, SalesOrder.Status.RETURN_REQUESTED),
}


def create_and_confirm_order(*, serializer, created_by):
    """Persist a valid submitted order and its confirmation effects atomically."""

    with transaction.atomic():
        order = serializer.save()
        return confirm_pending_order(order_id=order.pk, created_by=created_by)


def confirm_pending_order(*, order_id, created_by, return_event=False):
    """Confirm one pending order after locking and validating all stock demand.

    ``return_event`` keeps the original order-only service result stable for
    existing callers while allowing the status endpoint to return its audit
    evidence without a second, race-prone lookup.
    """

    with transaction.atomic():
        try:
            order = SalesOrder.objects.select_for_update().get(pk=order_id)
        except SalesOrder.DoesNotExist as error:
            raise OrderConfirmationError(
                {"order": ["Order was not found."]}
            ) from error
        if order.status != SalesOrder.Status.PENDING:
            raise OrderConfirmationError(
                {"status": ["Only pending orders can be confirmed."]}
            )
        if not has_store_access(created_by, order.store):
            raise OrderConfirmationError(
                {"initiated_by": ["Actor does not have order-store access."]}
            )

        items = list(
            order.items.select_related("product", "variant").order_by("id")
        )
        if not items:
            raise OrderConfirmationError(
                {"items": ["A pending order requires at least one item."]}
            )

        stock_for_item = _lock_stock_for_items(order, items)
        demand_by_stock = defaultdict(int)
        for item in items:
            demand_by_stock[stock_for_item[item.pk].pk] += item.quantity
        for stock in stock_for_item.values():
            if stock.quantity_on_hand < demand_by_stock[stock.pk]:
                raise OrderConfirmationError(
                    {"items": ["Insufficient stock to confirm this order."]}
                )

        for item in items:
            item.unit_cost_snapshot = item.product.unit_cost
            item.save()

        for item in items:
            stock = stock_for_item[item.pk]
            apply_stock_adjustment(
                stock_unit_id=stock.pk,
                movement_type=InventoryMovement.MovementType.ORDER_CONFIRMATION_DEDUCTION,
                quantity_delta=-item.quantity,
                created_by=created_by,
                operation_id=_confirmation_operation_id(order, item),
                order_item=item,
            )

        order.status = SalesOrder.Status.CONFIRMED
        order.confirmed_at = timezone.now()
        order.save(update_fields={"status", "confirmed_at", "updated_at"})
        event = _record_status_event(
            order=order,
            from_status=SalesOrder.Status.PENDING,
            to_status=SalesOrder.Status.CONFIRMED,
            initiated_by=created_by,
        )
    if return_event:
        return order, event
    return order


def transition_order_status(*, order_id, to_status, initiated_by):
    """Apply one supported status transition and append immutable evidence."""

    with transaction.atomic():
        try:
            order = SalesOrder.objects.select_for_update().select_related("store").get(
                pk=order_id
            )
        except SalesOrder.DoesNotExist as error:
            raise OrderTransitionError({"order": ["Order was not found."]}) from error
        if not has_store_access(initiated_by, order.store):
            raise OrderTransitionError(
                {"initiated_by": ["Actor does not have order-store access."]}
            )
        if to_status not in {choice for choice, _ in SalesOrder.Status.choices}:
            raise OrderTransitionError({"status": ["Unsupported order status."]})
        if order.status == to_status:
            raise OrderTransitionError({"status": ["Order is already in this status."]})

        if (order.status, to_status) == (
            SalesOrder.Status.PENDING,
            SalesOrder.Status.CONFIRMED,
        ):
            return confirm_pending_order(
                order_id=order.pk,
                created_by=initiated_by,
                return_event=True,
            )
        if (order.status, to_status) not in SAFE_NO_EFFECT_TRANSITIONS:
            raise OrderTransitionError(
                {"status": ["This transition requires a later approved side-effect workflow."]}
            )
        if to_status == SalesOrder.Status.PENDING and not order.items.exists():
            raise OrderTransitionError(
                {"items": ["A pending order requires at least one item."]}
            )

        from_status = order.status
        order.status = to_status
        _apply_transition_timestamp(order, to_status)
        order.save()
        event = _record_status_event(
            order=order,
            from_status=from_status,
            to_status=to_status,
            initiated_by=initiated_by,
        )
    return order, event


def _apply_transition_timestamp(order, to_status):
    if to_status == SalesOrder.Status.CANCELLED:
        order.cancelled_at = timezone.now()
    elif to_status == SalesOrder.Status.DELIVERED:
        order.delivered_at = timezone.now()
    elif to_status == SalesOrder.Status.RETURN_REQUESTED:
        order.return_requested_at = timezone.now()


def _record_status_event(*, order, from_status, to_status, initiated_by):
    return OrderStatusEvent.objects.create(
        order=order,
        from_status=from_status,
        to_status=to_status,
        initiated_by=initiated_by,
    )


def _lock_stock_for_items(order, items):
    """Acquire stock locks in a deterministic product/variant order."""

    items_by_key = defaultdict(list)
    for item in items:
        items_by_key[(item.product_id, item.variant_id)].append(item)

    stock_for_item = {}
    for product_id, variant_id in sorted(
        items_by_key, key=lambda key: (str(key[0]), str(key[1] or ""))
    ):
        try:
            stock = StockUnit.objects.select_for_update().get(
                store_id=order.store_id,
                product_id=product_id,
                variant_id=variant_id,
            )
        except StockUnit.DoesNotExist as error:
            raise OrderConfirmationError(
                {"items": ["Stock is not configured for an order item."]}
            ) from error
        for item in items_by_key[(product_id, variant_id)]:
            stock_for_item[item.pk] = stock
    return stock_for_item


def _confirmation_operation_id(order, item):
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"selleros:order-confirmation:{order.pk}:{item.pk}",
    )
