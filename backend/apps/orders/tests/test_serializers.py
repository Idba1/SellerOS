from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.customers.models import Customer
from apps.orders.models import SalesOrder
from apps.orders.serializers import OrderCreateSerializer
from tests.factories import FactoryContext, create_store_graph


class OrderCreateSerializerTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="order-create-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="order-create-b"))
        self.customer_a = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic Customer A"
        )
        self.customer_b = Customer.objects.create(
            store=self.graph_b.store, display_name="Synthetic Customer B"
        )
        self.standalone = Product.objects.create(
            store=self.graph_a.store,
            name="Standalone Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.variant_product = Product.objects.create(
            store=self.graph_a.store,
            name="Variant Product",
            selling_price=Decimal("120.00"),
            unit_cost=Decimal("30.00"),
            has_variants=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product, name="Blue"
        )
        self.foreign_product = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Product",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )

    def serializer(self, data):
        return OrderCreateSerializer(data=data, context={"store": self.graph_a.store})

    def valid_payload(self):
        return {
            "customer_id": str(self.customer_a.pk),
            "items": [
                {"product_id": str(self.standalone.pk), "quantity": 2},
                {
                    "product_id": str(self.variant_product.pk),
                    "variant_id": str(self.variant.pk),
                    "quantity": 1,
                },
            ],
            "order_discount": "10.00",
            "seller_delivery_cost": "25.00",
        }

    def test_valid_payload_creates_pending_server_priced_snapshot_order(self):
        serializer = self.serializer(self.valid_payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)
        order = serializer.save()

        self.assertEqual(order.store, self.graph_a.store)
        self.assertEqual(order.customer, self.customer_a)
        self.assertEqual(order.status, SalesOrder.Status.PENDING)
        self.assertEqual(order.currency_code, "BDT")
        self.assertEqual(order.items.count(), 2)
        first = order.items.get(product=self.standalone)
        second = order.items.get(product=self.variant_product)
        self.assertEqual(first.selling_price_snapshot, Decimal("100.00"))
        self.assertEqual(first.unit_cost_snapshot, None)
        self.assertEqual(first.product_name_snapshot, "Standalone Product")
        self.assertEqual(second.variant_name_snapshot, "Blue")
        self.assertEqual(first.discount_allocation, Decimal("6.25"))
        self.assertEqual(second.discount_allocation, Decimal("3.75"))
        self.assertEqual(
            first.discount_allocation + second.discount_allocation, Decimal("10.00")
        )

    def test_foreign_and_inactive_references_are_rejected(self):
        inactive_product = Product.objects.create(
            store=self.graph_a.store,
            name="Inactive Product",
            selling_price=Decimal("90.00"),
            unit_cost=Decimal("20.00"),
            is_active=False,
        )
        cases = (
            (
                {"customer_id": str(self.customer_b.pk), "items": self.valid_payload()["items"]},
                "customer_id",
            ),
            (
                {"items": [{"product_id": str(self.foreign_product.pk), "quantity": 1}]},
                "items",
            ),
            (
                {"items": [{"product_id": str(inactive_product.pk), "quantity": 1}]},
                "items",
            ),
        )
        for payload, field in cases:
            with self.subTest(payload=payload):
                serializer = self.serializer(payload)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_malformed_items_discount_and_client_owned_fields_are_rejected(self):
        cases = (
            ({"items": []}, "items"),
            (
                {"items": [{"product_id": str(self.standalone.pk), "quantity": 0}]},
                "items",
            ),
            (
                {"items": [{"product_id": str(self.variant_product.pk), "quantity": 1}]},
                "items",
            ),
            (
                {
                    "items": [{"product_id": str(self.standalone.pk), "quantity": 1}],
                    "order_discount": "101.00",
                },
                "order_discount",
            ),
            (
                {
                    "items": [{"product_id": str(self.standalone.pk), "quantity": 1}],
                    "status": "DELIVERED",
                },
                "status",
            ),
            (
                {
                    "items": [
                        {
                            "product_id": str(self.standalone.pk),
                            "quantity": 1,
                            "selling_price_snapshot": "1.00",
                        }
                    ]
                },
                "items",
            ),
        )
        for payload, field in cases:
            with self.subTest(payload=payload):
                serializer = self.serializer(payload)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)
