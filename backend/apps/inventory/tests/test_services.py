import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product
from apps.inventory.models import InventoryMovement, StockUnit
from apps.inventory.services import StockAdjustmentError, apply_stock_adjustment
from tests.factories import FactoryContext, create_store_graph


class StockAdjustmentServiceTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="inventory-service"))
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Service Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.stock_unit = StockUnit.objects.create(
            store=self.graph.store,
            product=self.product,
            quantity_on_hand=5,
        )

    def test_success_updates_cached_balance_and_creates_matching_movement(self):
        operation_id = uuid.uuid4()

        movement = apply_stock_adjustment(
            stock_unit_id=self.stock_unit.pk,
            movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
            quantity_delta=3,
            reason="Cycle count correction",
            created_by=self.graph.staff,
            operation_id=operation_id,
        )

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 8)
        self.assertEqual(InventoryMovement.objects.count(), 1)
        self.assertEqual(movement.stock_unit_id, self.stock_unit.pk)
        self.assertEqual(movement.store_id, self.graph.store.pk)
        self.assertEqual(movement.operation_id, operation_id)

    def test_overdraw_or_invalid_movement_changes_neither_record(self):
        with self.assertRaises(StockAdjustmentError):
            apply_stock_adjustment(
                stock_unit_id=self.stock_unit.pk,
                movement_type=InventoryMovement.MovementType.ORDER_CONFIRMATION_DEDUCTION,
                quantity_delta=-6,
                created_by=self.graph.owner,
            )
        with self.assertRaises(ValidationError):
            apply_stock_adjustment(
                stock_unit_id=self.stock_unit.pk,
                movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                quantity_delta=1,
                created_by=self.graph.owner,
            )

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 5)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_duplicate_operation_is_rejected_without_a_second_balance_change(self):
        operation_id = uuid.uuid4()
        arguments = {
            "stock_unit_id": self.stock_unit.pk,
            "movement_type": InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
            "quantity_delta": 2,
            "reason": "Cycle count correction",
            "created_by": self.graph.owner,
            "operation_id": operation_id,
        }
        apply_stock_adjustment(**arguments)

        with self.assertRaises(StockAdjustmentError):
            apply_stock_adjustment(**arguments)

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 7)
        self.assertEqual(InventoryMovement.objects.count(), 1)
