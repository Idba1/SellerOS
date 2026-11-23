from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.catalog.serializers import (
    ProductSerializer,
    ProductVariantSerializer,
    ProductVariantWriteSerializer,
    ProductWriteSerializer,
)
from tests.factories import FactoryContext, create_store_graph


class ProductSerializerTests(TestCase):
    def setUp(self):
        self.store = create_store_graph(FactoryContext(namespace="catalog-serializers")).store
        self.payload = {
            "name": " Harbor Tote ",
            "category": " Carry goods ",
            "selling_price": "850.00",
            "unit_cost": "430.00",
            "has_variants": False,
            "is_active": True,
        }

    def create_product(self, **overrides):
        values = {
            "store": self.store,
            "name": "Product",
            "selling_price": Decimal("100.00"),
            "unit_cost": Decimal("20.00"),
            "has_variants": True,
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def test_valid_product_payload_normalizes_and_uses_server_store_context(self):
        serializer = ProductWriteSerializer(data=self.payload, context={"store": self.store})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()

        self.assertEqual(product.store, self.store)
        self.assertEqual(product.name, "Harbor Tote")
        self.assertEqual(product.category, "Carry goods")
        self.assertEqual(product.selling_price, Decimal("850.00"))
        self.assertEqual(product.unit_cost, Decimal("430.00"))

    def test_product_payload_rejects_invalid_decimals_blank_name_and_store_selector(self):
        cases = (
            ({**self.payload, "selling_price": "0.00"}, "selling_price"),
            ({**self.payload, "selling_price": "1.001"}, "selling_price"),
            ({**self.payload, "unit_cost": "-0.01"}, "unit_cost"),
            ({**self.payload, "name": "   "}, "name"),
            ({**self.payload, "store_id": str(self.store.id)}, "store_id"),
        )

        for payload, field in cases:
            with self.subTest(field=field, payload=payload):
                serializer = ProductWriteSerializer(
                    data=payload, context={"store": self.store}
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_product_update_accepts_active_state_and_read_serializer_excludes_store(self):
        product = self.create_product()
        serializer = ProductWriteSerializer(
            instance=product, data={"is_active": False}, partial=True
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        representation = ProductSerializer(updated).data

        self.assertFalse(updated.is_active)
        self.assertNotIn("store", representation)
        self.assertNotIn("store_id", representation)
        self.assertEqual(representation["id"], str(product.id))


class ProductVariantSerializerTests(TestCase):
    def setUp(self):
        self.store = create_store_graph(FactoryContext(namespace="variant-serializers")).store

    def create_product(self, **overrides):
        values = {
            "store": self.store,
            "name": "Organizer",
            "selling_price": Decimal("1200.00"),
            "unit_cost": Decimal("690.00"),
            "has_variants": True,
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def test_variant_payload_requires_server_product_context_and_variant_product(self):
        valid = ProductVariantWriteSerializer(
            data={"name": " Sky ", "is_active": True},
            context={"product": self.create_product()},
        )
        missing_context = ProductVariantWriteSerializer(data={"name": "Sky"})
        standalone = ProductVariantWriteSerializer(
            data={"name": "Sky"},
            context={"product": self.create_product(name="Standalone", has_variants=False)},
        )

        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.save().name, "Sky")
        self.assertFalse(missing_context.is_valid())
        self.assertIn("non_field_errors", missing_context.errors)
        self.assertFalse(standalone.is_valid())
        self.assertIn("product", standalone.errors)

    def test_variant_payload_rejects_duplicate_or_client_parent_selector(self):
        product = self.create_product()
        ProductVariant.objects.create(product=product, name="Dawn")

        duplicate = ProductVariantWriteSerializer(
            data={"name": "dawn"}, context={"product": product}
        )
        selector = ProductVariantWriteSerializer(
            data={"name": "Sky", "product_id": str(product.id)},
            context={"product": product},
        )

        self.assertFalse(duplicate.is_valid())
        self.assertIn("name", duplicate.errors)
        self.assertFalse(selector.is_valid())
        self.assertIn("product_id", selector.errors)

    def test_variant_read_serializer_exposes_parent_identifier_without_write_access(self):
        product = self.create_product()
        variant = ProductVariant.objects.create(product=product, name="Dawn")

        representation = ProductVariantSerializer(variant).data

        self.assertEqual(representation["product_id"], str(product.id))
        self.assertNotIn("store", representation)
