from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import InventoryMovement, StockUnit
from tests.factories import FactoryContext, create_store_graph


class InventoryModelTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="inventory-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="inventory-b"))
        self.standalone = Product.objects.create(
            store=self.graph_a.store,
            name="Standalone",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.stock_unit = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.standalone,
            quantity_on_hand=5,
            low_stock_threshold=3,
        )

    def test_cached_balance_uses_seller_threshold_without_guessing_when_missing(self):
        self.assertFalse(self.stock_unit.is_low_stock)

        self.stock_unit.quantity_on_hand = 3
        self.stock_unit.save()
        self.assertTrue(self.stock_unit.is_low_stock)

        self.stock_unit.low_stock_threshold = None
        self.stock_unit.save()
        self.assertFalse(self.stock_unit.is_low_stock)

    def test_stock_unit_requires_matching_store_product_and_variant_mode(self):
        variant_product = Product.objects.create(
            store=self.graph_a.store,
            name="Variant Product",
            selling_price=Decimal("200.00"),
            unit_cost=Decimal("50.00"),
            has_variants=True,
        )
        variant = ProductVariant.objects.create(product=variant_product, name="Sky")
        variant_unit = StockUnit.objects.create(
            store=self.graph_a.store,
            product=variant_product,
            variant=variant,
        )
        self.assertEqual(variant_unit.variant, variant)

        with self.assertRaises(ValidationError):
            StockUnit.objects.create(
                store=self.graph_b.store,
                product=self.standalone,
            )
        with self.assertRaises(ValidationError):
            StockUnit.objects.create(
                store=self.graph_a.store,
                product=variant_product,
            )
        with self.assertRaises(ValidationError):
            StockUnit.objects.create(
                store=self.graph_a.store,
                product=self.standalone,
                variant=variant,
            )

    def test_movement_validates_direction_reason_reversal_and_creator_store_access(self):
        opening = InventoryMovement.objects.create(
            store=self.graph_a.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.OPENING_BALANCE,
            quantity_delta=5,
            created_by=self.graph_a.owner,
        )
        deduction = InventoryMovement.objects.create(
            store=self.graph_a.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.ORDER_CONFIRMATION_DEDUCTION,
            quantity_delta=-2,
            created_by=self.graph_a.staff,
        )
        restoration = InventoryMovement.objects.create(
            store=self.graph_a.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.ORDER_RETURN_RESTORATION,
            quantity_delta=2,
            reversal_of=deduction,
            created_by=self.graph_a.owner,
        )

        self.assertIsNotNone(opening.operation_id)
        self.assertEqual(restoration.reversal_of, deduction)

        cases = (
            {
                "movement_type": InventoryMovement.MovementType.OPENING_BALANCE,
                "quantity_delta": -1,
            },
            {
                "movement_type": InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
                "quantity_delta": 1,
            },
            {
                "movement_type": InventoryMovement.MovementType.ORDER_RETURN_RESTORATION,
                "quantity_delta": 1,
            },
            {
                "movement_type": InventoryMovement.MovementType.ORDER_CONFIRMATION_DEDUCTION,
                "quantity_delta": -1,
                "created_by": self.graph_b.owner,
            },
        )
        for overrides in cases:
            values = {
                "store": self.graph_a.store,
                "stock_unit": self.stock_unit,
                "created_by": self.graph_a.owner,
            }
            values.update(overrides)
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                InventoryMovement.objects.create(**values)

    def test_created_movement_is_immutable_and_cannot_be_deleted(self):
        movement = InventoryMovement.objects.create(
            store=self.graph_a.store,
            stock_unit=self.stock_unit,
            movement_type=InventoryMovement.MovementType.OPENING_BALANCE,
            quantity_delta=5,
            created_by=self.graph_a.owner,
        )

        movement.quantity_delta = 6
        with self.assertRaises(ValidationError):
            movement.save()
        with self.assertRaises(ValidationError):
            movement.delete()
