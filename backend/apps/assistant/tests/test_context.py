from decimal import Decimal

from django.test import TestCase

from apps.assistant.context import build_assistant_reply_context
from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class AssistantContextBuilderTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="context-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="context-b"))

        self.tote = Product.objects.create(
            store=self.graph_a.store,
            name="Harbor Canvas Tote",
            selling_price=Decimal("850.00"),
            unit_cost=Decimal("350.00"),
        )
        self.tote_stock = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.tote,
            quantity_on_hand=4,
        )
        self.shirt = Product.objects.create(
            store=self.graph_a.store,
            name="Coastal Shirt",
            selling_price=Decimal("1200.00"),
            unit_cost=Decimal("500.00"),
            has_variants=True,
        )
        self.sky = ProductVariant.objects.create(product=self.shirt, name="Sky")
        self.sky_stock = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.shirt,
            variant=self.sky,
            quantity_on_hand=1,
        )
        self.foreign = Product.objects.create(
            store=self.graph_b.store,
            name="Foreign Product",
            selling_price=Decimal("999.00"),
            unit_cost=Decimal("100.00"),
        )
        self.foreign_stock = StockUnit.objects.create(
            store=self.graph_b.store,
            product=self.foreign,
            quantity_on_hand=9,
        )

    def test_context_contains_only_message_relevant_same_store_fact_and_sources(self):
        context = build_assistant_reply_context(
            self.graph_a.owner,
            customer_message="Please confirm Harbor Canvas Tote price and availability.",
        )

        self.assertEqual(len(context.facts), 1)
        fact = context.facts[0]
        self.assertEqual(fact.product_name, "Harbor Canvas Tote")
        self.assertEqual(fact.selling_price, Decimal("850.00"))
        self.assertEqual(fact.availability, "available")
        self.assertEqual(
            [(source.source_type, source.source_id) for source in fact.sources],
            [("product", self.tote.pk), ("stock_unit", self.tote_stock.pk)],
        )
        self.assertEqual(fact.sources[0].as_of, self.tote.updated_at)
        self.assertEqual(fact.sources[1].as_of, self.tote_stock.updated_at)
        self.assertNotIn("quantity_on_hand", fact.__dataclass_fields__)
        self.assertNotIn("unit_cost", fact.__dataclass_fields__)
        self.assertNotIn("store_id", fact.__dataclass_fields__)

    def test_variant_fact_has_traceable_variant_source(self):
        context = build_assistant_reply_context(
            self.graph_a.staff,
            customer_message="Is the Sky option available?",
        )

        self.assertEqual(len(context.facts), 1)
        fact = context.facts[0]
        self.assertEqual(fact.variant_name, "Sky")
        self.assertEqual(
            [source.source_type for source in fact.sources],
            ["product", "stock_unit", "product_variant"],
        )
        self.assertEqual(fact.sources[2].source_id, self.sky.pk)
        self.assertEqual(fact.sources[2].as_of, self.sky.updated_at)

    def test_contact_identifiers_are_removed_from_returned_message_context(self):
        context = build_assistant_reply_context(
            self.graph_a.owner,
            customer_message=(
                "My email is buyer@example.test and phone is +8801712345678. "
                "Is Harbor Canvas Tote available?"
            ),
        )

        self.assertTrue(context.contact_identifiers_redacted)
        self.assertNotIn("buyer@example.test", context.message_for_provider)
        self.assertNotIn("+8801712345678", context.message_for_provider)
        self.assertIn("[email removed]", context.message_for_provider)
        self.assertIn("[phone removed]", context.message_for_provider)
        self.assertEqual(len(context.facts), 1)

    def test_foreign_product_name_cannot_enter_context(self):
        context = build_assistant_reply_context(
            self.graph_a.owner,
            customer_message="What is the price of Foreign Product?",
        )

        self.assertEqual(context.facts, ())
        self.assertNotIn(self.foreign.name, str(context.facts))
        self.assertNotIn(str(self.foreign_stock.pk), str(context.facts))
