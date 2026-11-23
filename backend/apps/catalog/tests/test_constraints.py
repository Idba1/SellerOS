from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from tests.factories import FactoryContext, create_store_graph


class CatalogDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.store = create_store_graph(FactoryContext(namespace="catalog-constraints")).store

    def create_product(self, **overrides):
        values = {
            "store": self.store,
            "name": "Constraint Product",
            "selling_price": Decimal("100.00"),
            "unit_cost": Decimal("20.00"),
            "has_variants": True,
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def test_price_and_cost_checks_reject_bulk_insert_or_update(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.bulk_create(
                [
                    Product(
                        store=self.store,
                        name="Invalid Price",
                        selling_price=Decimal("0.00"),
                    )
                ]
            )

        product = self.create_product()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(unit_cost=Decimal("-0.01"))

    def test_variant_database_constraint_rejects_case_insensitive_duplicate(self):
        product = self.create_product()
        ProductVariant.objects.create(product=product, name="Dawn")

        duplicate = ProductVariant(product=product, name="dawn")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.bulk_create([duplicate])
