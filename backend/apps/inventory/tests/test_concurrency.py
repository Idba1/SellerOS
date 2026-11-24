"""PostgreSQL transaction-boundary tests for atomic stock adjustment."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.db import connection, connections
from django.test import TransactionTestCase

from apps.accounts.models import Account
from apps.catalog.models import Product
from apps.inventory.models import InventoryMovement, StockUnit
from apps.inventory.services import StockAdjustmentError, apply_stock_adjustment
from tests.factories import FactoryContext, create_store_graph


class StockConcurrencyTests(TransactionTestCase):
    """Use committed worker transactions; TestCase's outer transaction is unsuitable."""

    def setUp(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.graph = create_store_graph(FactoryContext(namespace="inventory-race"))
        self.product = Product.objects.create(
            store=self.graph.store,
            name="Concurrent Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.stock_unit = StockUnit.objects.create(
            store=self.graph.store,
            product=self.product,
            quantity_on_hand=5,
        )

    def apply_concurrently(self, deltas):
        """Start independent transactions together and return their observable results."""

        barrier = Barrier(len(deltas))
        stock_unit_id = self.stock_unit.pk
        owner_id = self.graph.owner.pk

        def worker(index, quantity_delta):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                owner = Account.objects.get(pk=owner_id)
                movement = apply_stock_adjustment(
                    stock_unit_id=stock_unit_id,
                    movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                    quantity_delta=quantity_delta,
                    reason=f"Concurrent adjustment {index}",
                    created_by=owner,
                )
                return "applied", movement.pk
            except StockAdjustmentError:
                return "rejected", None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(deltas)) as executor:
            futures = [
                executor.submit(worker, index, delta)
                for index, delta in enumerate(deltas, start=1)
            ]
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_increments_preserve_both_changes_and_movements(self):
        results = self.apply_concurrently((2, 3))

        self.stock_unit.refresh_from_db()
        self.assertEqual([result for result, _ in results], ["applied", "applied"])
        self.assertEqual(self.stock_unit.quantity_on_hand, 10)
        movements = InventoryMovement.objects.filter(stock_unit=self.stock_unit)
        self.assertEqual(movements.count(), 2)
        self.assertEqual(sum(movement.quantity_delta for movement in movements), 5)

    def test_concurrent_overdraw_allows_only_one_deduction(self):
        results = self.apply_concurrently((-4, -4))

        self.stock_unit.refresh_from_db()
        self.assertCountEqual(
            [result for result, _ in results], ["applied", "rejected"]
        )
        self.assertEqual(self.stock_unit.quantity_on_hand, 1)
        movements = InventoryMovement.objects.filter(stock_unit=self.stock_unit)
        self.assertEqual(movements.count(), 1)
        self.assertEqual(movements.get().quantity_delta, -4)

    def test_balance_save_failure_rolls_back_preceding_movement(self):
        with patch.object(
            StockUnit,
            "save",
            side_effect=RuntimeError("simulated balance persistence failure"),
        ):
            with self.assertRaises(RuntimeError):
                apply_stock_adjustment(
                    stock_unit_id=self.stock_unit.pk,
                    movement_type=InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                    quantity_delta=2,
                    reason="Rollback boundary test",
                    created_by=self.graph.owner,
                )

        self.stock_unit.refresh_from_db()
        self.assertEqual(self.stock_unit.quantity_on_hand, 5)
        self.assertFalse(
            InventoryMovement.objects.filter(stock_unit=self.stock_unit).exists()
        )
