from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import NotFound

from apps.assistant.retrieval import (
    AVAILABILITY_AVAILABLE,
    AVAILABILITY_UNAVAILABLE,
    AssistantRetrievalError,
    retrieve_product_stock_fact,
    retrieve_relevant_product_stock_facts,
)
from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import StockUnit
from tests.factories import FactoryContext, create_store_graph


class AssistantProductStockRetrievalTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="assistant-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="assistant-b"))

        self.tote = Product.objects.create(
            store=self.graph_a.store,
            name="Harbor Canvas Tote",
            selling_price=Decimal("850.00"),
            unit_cost=Decimal("350.00"),
        )
        self.tote_stock = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.tote,
            quantity_on_hand=7,
        )
        self.mug = Product.objects.create(
            store=self.graph_a.store,
            name="River Mug",
            selling_price=Decimal("250.00"),
            unit_cost=Decimal("80.00"),
        )
        StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.mug,
            quantity_on_hand=3,
        )
        self.shirt = Product.objects.create(
            store=self.graph_a.store,
            name="Coastal Shirt",
            selling_price=Decimal("1200.00"),
            unit_cost=Decimal("500.00"),
            has_variants=True,
            is_active=False,
        )
        self.sky = ProductVariant.objects.create(product=self.shirt, name="Sky")
        self.sky_stock = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.shirt,
            variant=self.sky,
            quantity_on_hand=0,
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

    def test_known_same_store_question_returns_current_minimized_fact(self):
        facts = retrieve_relevant_product_stock_facts(
            self.graph_a.owner,
            customer_message="What is the price of Harbor Canvas Tote and is it available?",
        )

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact.stock_unit_id, self.tote_stock.pk)
        self.assertEqual(fact.product_id, self.tote.pk)
        self.assertEqual(fact.product_name, "Harbor Canvas Tote")
        self.assertEqual(fact.selling_price, Decimal("850.00"))
        self.assertEqual(fact.currency_code, "BDT")
        self.assertEqual(fact.availability, AVAILABILITY_AVAILABLE)
        self.assertTrue(fact.product_is_active)
        self.assertNotIn("quantity_on_hand", fact.__dataclass_fields__)
        self.assertNotIn("unit_cost", fact.__dataclass_fields__)

    def test_variant_name_retrieves_current_inactive_and_unavailable_states(self):
        facts = retrieve_relevant_product_stock_facts(
            self.graph_a.staff,
            customer_message="Is the Sky option available?",
        )

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact.stock_unit_id, self.sky_stock.pk)
        self.assertEqual(fact.variant_name, "Sky")
        self.assertFalse(fact.product_is_active)
        self.assertTrue(fact.variant_is_active)
        self.assertEqual(fact.availability, AVAILABILITY_UNAVAILABLE)

    def test_foreign_stock_is_not_retrievable_or_disclosed(self):
        matching_facts = retrieve_relevant_product_stock_facts(
            self.graph_a.owner,
            customer_message="What is the price of Foreign Product?",
        )

        self.assertEqual(matching_facts, ())
        with self.assertRaisesRegex(NotFound, "No matching catalogue stock record"):
            retrieve_product_stock_fact(
                self.graph_a.owner,
                stock_unit_id=self.foreign_stock.pk,
            )

    def test_blank_and_overlong_messages_fail_before_catalogue_query(self):
        with self.assertRaises(AssistantRetrievalError):
            retrieve_relevant_product_stock_facts(
                self.graph_a.owner,
                customer_message="   ",
            )
        with self.assertRaises(AssistantRetrievalError):
            retrieve_relevant_product_stock_facts(
                self.graph_a.owner,
                customer_message="x" * 2_001,
            )
