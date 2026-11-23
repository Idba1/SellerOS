from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from tests.factories import FactoryContext, create_store_graph


class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.store = create_store_graph(FactoryContext(namespace="catalog")).store

    def create_product(self, **overrides):
        values = {
            "store": self.store,
            "name": " Harbor Tote ",
            "category": " Carry goods ",
            "selling_price": Decimal("850.00"),
            "unit_cost": Decimal("430.00"),
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def test_product_is_store_owned_and_normalizes_optional_category(self):
        product = self.create_product()

        self.assertEqual(product.store, self.store)
        self.assertEqual(self.store.products.get(pk=product.pk), product)
        self.assertEqual(product.name, "Harbor Tote")
        self.assertEqual(product.category, "Carry goods")
        self.assertTrue(product.is_active)
        self.assertFalse(product.has_variants)

    def test_product_requires_positive_price_and_nonnegative_or_unknown_cost(self):
        for field, value in (("selling_price", Decimal("0.00")), ("selling_price", Decimal("-1.00")), ("unit_cost", Decimal("-0.01"))):
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                self.create_product(**{field: value})

        unknown_cost = self.create_product(name="Unknown Cost", unit_cost=None)
        self.assertIsNone(unknown_cost.unit_cost)

    def test_variant_belongs_to_a_variant_based_product_and_inherits_store_scope(self):
        product = self.create_product(name="Organizer", has_variants=True)
        variant = ProductVariant.objects.create(product=product, name=" Sky ")

        self.assertEqual(variant.name, "Sky")
        self.assertEqual(variant.product.store, self.store)
        self.assertEqual(product.variants.get(pk=variant.pk), variant)

        standalone = self.create_product(name="Standalone")
        with self.assertRaises(ValidationError):
            ProductVariant.objects.create(product=standalone, name="Not Allowed")

    def test_variant_name_is_case_insensitively_unique_per_product(self):
        product = self.create_product(name="Cup", has_variants=True)
        ProductVariant.objects.create(product=product, name="Dawn")

        with self.assertRaises(ValidationError):
            ProductVariant.objects.create(product=product, name="dawn")

        other_product = self.create_product(name="Other Cup", has_variants=True)
        self.assertEqual(
            ProductVariant.objects.create(product=other_product, name="Dawn").name,
            "Dawn",
        )

    def test_product_deletion_is_protected_while_variants_exist(self):
        product = self.create_product(name="Protected", has_variants=True)
        ProductVariant.objects.create(product=product, name="Blue")

        with self.assertRaises(ProtectedError):
            product.delete()
