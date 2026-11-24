import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.catalog.models import Product
from apps.inventory.models import InventoryMovement, StockUnit
from tests.factories import FactoryContext, create_store_graph


class InventoryDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.graph = create_store_graph(FactoryContext(namespace="inventory-constraints"))
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Constraint Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.stock_unit = StockUnit.objects.create(
            store=self.graph.store,
            product=self.product,
        )

    def test_cached_balance_constraints_reject_negative_direct_writes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockUnit.objects.filter(pk=self.stock_unit.pk).update(quantity_on_hand=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockUnit.objects.filter(pk=self.stock_unit.pk).update(low_stock_threshold=-1)

    def test_movement_constraints_reject_zero_and_duplicate_operation(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryMovement.objects.bulk_create(
                [
                    InventoryMovement(
                        store=self.graph.store,
                        stock_unit=self.stock_unit,
                        movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                        quantity_delta=0,
                        created_by=self.graph.owner,
                    )
                ]
            )

        operation_id = uuid.uuid4()
        InventoryMovement.objects.create(
            store=self.graph.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.OPENING_BALANCE,
            quantity_delta=5,
            operation_id=operation_id,
            created_by=self.graph.owner,
        )
        duplicate = InventoryMovement(
            store=self.graph.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.OPENING_BALANCE,
            quantity_delta=5,
            operation_id=operation_id,
            created_by=self.graph.owner,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryMovement.objects.bulk_create([duplicate])
