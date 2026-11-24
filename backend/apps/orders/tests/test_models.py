from datetime import datetime, timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.customers.models import Customer
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class SalesOrderModelTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="orders-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="orders-b"))
        self.customer_a = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic Buyer A"
        )
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Synthetic Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Synthetic Product B",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )

    def create_order(self, **overrides):
        values = {
            "store": self.graph_a.store,
            "customer": self.customer_a,
            "status": SalesOrder.Status.DELIVERED,
            "delivered_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return SalesOrder.objects.create(**values)

    def test_order_requires_same_store_customer_and_bdt(self):
        order = self.create_order()
        self.assertEqual(order.customer, self.customer_a)

        foreign_customer = Customer.objects.create(
            store=self.graph_b.store, display_name="Foreign Buyer"
        )
        with self.assertRaises(ValidationError):
            self.create_order(customer=foreign_customer)
        with self.assertRaises(ValidationError):
            self.create_order(currency_code="USD")

    def test_item_uses_snapshots_and_requires_same_store_product(self):
        order = self.create_order()
        item = OrderItem.objects.create(
            order=order,
            product=self.product_a,
            product_name_snapshot="Synthetic Product A",
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("20.00"),
        )
        self.assertEqual(item.order, order)
        self.assertEqual(order.items.get(pk=item.pk), item)

        with self.assertRaises(ValidationError):
            OrderItem.objects.create(
                order=order,
                product=self.product_b,
                product_name_snapshot="Synthetic Product B",
                quantity=1,
                selling_price_snapshot=Decimal("100.00"),
            )

    def test_item_snapshots_survive_later_catalogue_changes(self):
        order = self.create_order()
        item = OrderItem.objects.create(
            order=order,
            product=self.product_a,
            product_name_snapshot="Original Snapshot Name",
            quantity=2,
            selling_price_snapshot=Decimal("100.00"),
            unit_cost_snapshot=Decimal("20.00"),
        )

        self.product_a.name = "Changed Catalogue Name"
        self.product_a.selling_price = Decimal("999.00")
        self.product_a.unit_cost = Decimal("888.00")
        self.product_a.save()
        item.refresh_from_db()

        self.assertEqual(item.product_name_snapshot, "Original Snapshot Name")
        self.assertEqual(item.selling_price_snapshot, Decimal("100.00"))
        self.assertEqual(item.unit_cost_snapshot, Decimal("20.00"))

    def test_item_validates_variant_and_transaction_value_boundaries(self):
        order = self.create_order()
        variant_product = Product.objects.create(
            store=self.graph_a.store,
            name="Variant Product",
            selling_price=Decimal("120.00"),
            unit_cost=Decimal("30.00"),
            has_variants=True,
        )
        variant = ProductVariant.objects.create(product=variant_product, name="Blue")
        item = OrderItem.objects.create(
            order=order,
            product=variant_product,
            variant=variant,
            product_name_snapshot="Variant Product",
            variant_name_snapshot="Blue",
            quantity=1,
            selling_price_snapshot=Decimal("120.00"),
            unit_cost_snapshot=None,
        )
        self.assertEqual(item.variant, variant)

        cases = (
            {
                "product": self.product_a,
                "variant": variant,
                "product_name_snapshot": "Synthetic Product A",
                "quantity": 1,
                "selling_price_snapshot": Decimal("100.00"),
            },
            {
                "product": self.product_a,
                "product_name_snapshot": "Synthetic Product A",
                "quantity": 0,
                "selling_price_snapshot": Decimal("100.00"),
            },
            {
                "product": self.product_a,
                "product_name_snapshot": "Synthetic Product A",
                "quantity": 1,
                "selling_price_snapshot": Decimal("0.00"),
            },
            {
                "product": self.product_a,
                "product_name_snapshot": "Synthetic Product A",
                "quantity": 1,
                "selling_price_snapshot": Decimal("100.00"),
                "unit_cost_snapshot": Decimal("-0.01"),
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                OrderItem.objects.create(order=order, **values)

    def test_status_event_requires_authorized_actor_and_is_immutable(self):
        order = self.create_order()
        event = OrderStatusEvent.objects.create(
            order=order,
            from_status=SalesOrder.Status.SHIPPED,
            to_status=SalesOrder.Status.DELIVERED,
            initiated_by=self.graph_a.owner,
        )
        self.assertEqual(event.order, order)

        with self.assertRaises(ValidationError):
            OrderStatusEvent.objects.create(
                order=order,
                from_status=SalesOrder.Status.DELIVERED,
                to_status=SalesOrder.Status.DELIVERED,
                initiated_by=self.graph_a.owner,
            )
        with self.assertRaises(ValidationError):
            OrderStatusEvent.objects.create(
                order=order,
                from_status=SalesOrder.Status.DELIVERED,
                to_status=SalesOrder.Status.RETURN_REQUESTED,
                initiated_by=self.graph_b.owner,
            )

        event.to_status = SalesOrder.Status.RETURN_REQUESTED
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
