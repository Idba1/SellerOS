from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.catalog.models import Product
from apps.inventory.models import InventoryMovement, StockUnit
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from apps.orders.serializers import OrderCreateSerializer
from apps.orders.services import (
    OrderConfirmationError,
    confirm_pending_order,
    create_and_confirm_order,
)
from tests.factories import FactoryContext, create_store_graph


class OrderConfirmationServiceTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="order-confirm"))
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Confirm Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("25.00"),
        )
        self.stock_unit = StockUnit.objects.create(
            store=self.graph.store,
            product=self.product,
            quantity_on_hand=5,
        )

    def serializer_for(self, quantities):
        serializer = OrderCreateSerializer(
            data={
                "items": [
                    {"product_id": str(self.product.pk), "quantity": quantity}
                    for quantity in quantities
                ]
            },
            context={"store": self.graph.store},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer

    def test_create_and_confirm_commits_order_cost_snapshot_stock_and_linked_movement(self):
        order = create_and_confirm_order(
            serializer=self.serializer_for([2]), created_by=self.graph.owner
        )

        self.assertEqual(order.status, SalesOrder.Status.CONFIRMED)
        self.assertIsNotNone(order.confirmed_at)
        item = order.items.get()
        self.assertEqual(item.unit_cost_snapshot, Decimal("25.00"))
        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 3)
        movement = InventoryMovement.objects.get()
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.ORDER_CONFIRMATION_DEDUCTION,
        )
        self.assertEqual(movement.quantity_delta, -2)
        self.assertEqual(movement.order_item, item)
        event = OrderStatusEvent.objects.get()
        self.assertEqual(event.order, order)
        self.assertEqual(event.from_status, SalesOrder.Status.PENDING)
        self.assertEqual(event.to_status, SalesOrder.Status.CONFIRMED)
        self.assertEqual(event.initiated_by, self.graph.owner)

    def test_insufficient_combined_demand_rolls_back_new_order_and_all_effects(self):
        with self.assertRaises(OrderConfirmationError):
            create_and_confirm_order(
                serializer=self.serializer_for([3, 3]), created_by=self.graph.owner
            )

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 5)
        self.assertFalse(SalesOrder.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())

    def test_stock_persistence_failure_rolls_back_new_order_and_movement(self):
        with patch.object(
            StockUnit,
            "save",
            side_effect=RuntimeError("simulated stock persistence failure"),
        ):
            with self.assertRaises(RuntimeError):
                create_and_confirm_order(
                    serializer=self.serializer_for([2]), created_by=self.graph.owner
                )

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 5)
        self.assertFalse(SalesOrder.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())

    def test_repeated_confirmation_cannot_create_a_second_deduction(self):
        order = create_and_confirm_order(
            serializer=self.serializer_for([2]), created_by=self.graph.owner
        )

        with self.assertRaises(OrderConfirmationError):
            confirm_pending_order(order_id=order.pk, created_by=self.graph.owner)

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 3)
        self.assertEqual(InventoryMovement.objects.count(), 1)
