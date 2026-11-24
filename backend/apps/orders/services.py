"""Atomic submitted-order confirmation and inventory deduction."""
import uuid
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import InventoryMovement, StockUnit
from apps.inventory.services import apply_stock_adjustment

from .models import SalesOrder


class OrderConfirmationError(ValidationError):
    """Raised when a submitted order cannot atomically become confirmed."""


def create_and_confirm_order(*, serializer, created_by):
    """Persist a valid submitted order and its confirmation effects atomically."""

    with transaction.atomic():
        order = serializer.save()
        return confirm_pending_order(order_id=order.pk, created_by=created_by)


def confirm_pending_order(*, order_id, created_by):
    """Confirm one pending order after locking and validating all stock demand."""

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
    return order


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
