from django.test import TestCase

from apps.accounts.models import Account, Store, StoreMembership
from tests.factories import FactoryContext, create_account, create_store_graph


class SharedFactoryTests(TestCase):
    def test_context_tokens_are_reproducible(self):
        first = FactoryContext(namespace="case")
        second = FactoryContext(namespace="case")

        self.assertEqual(first.next_token("account"), "case-account-001")
        self.assertEqual(first.next_token("account"), "case-account-002")
        self.assertEqual(second.next_token("account"), "case-account-001")

    def test_factory_rejects_non_synthetic_email_override(self):
        with self.assertRaises(ValueError):
            create_account(
                FactoryContext(namespace="safety"), email="person@real.example"
            )

    def test_factory_creates_valid_owner_store_and_active_staff_graph(self):
        graph = create_store_graph(FactoryContext(namespace="graph"))

        self.assertEqual(graph.owner.email, "graph-account-001@example.test")
        self.assertEqual(graph.store.owner, graph.owner)
        self.assertEqual(graph.store.timezone, "Asia/Dhaka")
        self.assertEqual(graph.store.currency_code, "BDT")
        self.assertIsNotNone(graph.staff)
        self.assertEqual(graph.staff.email, "graph-account-002@example.test")
        self.assertEqual(graph.staff_membership.store, graph.store)
        self.assertTrue(graph.staff_membership.is_active)
        self.assertEqual(Account.objects.count(), 2)
        self.assertEqual(Store.objects.count(), 1)
        self.assertEqual(StoreMembership.objects.count(), 1)

    def test_factory_can_create_an_isolated_owner_only_graph(self):
        graph = create_store_graph(
            FactoryContext(namespace="owner-only"), include_staff=False
        )

        self.assertIsNone(graph.staff)
        self.assertIsNone(graph.staff_membership)
        self.assertEqual(graph.store.owner, graph.owner)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(StoreMembership.objects.count(), 0)

    def test_same_context_creates_non_colliding_store_graphs(self):
        context = FactoryContext(namespace="multi")
        first = create_store_graph(context)
        second = create_store_graph(context, staff_active=False)

        self.assertNotEqual(first.owner.id, second.owner.id)
        self.assertNotEqual(first.store.id, second.store.id)
        self.assertNotEqual(first.staff.id, second.staff.id)
        self.assertFalse(second.staff_membership.is_active)
        self.assertEqual(Store.objects.count(), 2)
