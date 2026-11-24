from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.customers.models import Customer
from tests.factories import FactoryContext, create_store_graph


class CustomerModelTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="customers-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="customers-b"))

    def create_customer(self, **overrides):
        values = {
            "store": self.graph_a.store,
            "display_name": "  Synthetic Buyer A  ",
            "phone": " synthetic-contact-001 ",
            "email": " Synthetic.Buyer.A@Example.TEST ",
        }
        values.update(overrides)
        return Customer.objects.create(**values)

    def test_customer_is_store_owned_and_normalizes_minimal_contact_fields(self):
        customer = self.create_customer()

        self.assertEqual(customer.store, self.graph_a.store)
        self.assertEqual(customer.display_name, "Synthetic Buyer A")
        self.assertEqual(customer.phone, "synthetic-contact-001")
        self.assertEqual(customer.email, "Synthetic.Buyer.A@example.test")
        self.assertEqual(self.graph_a.store.customers.get(pk=customer.pk), customer)

    def test_customer_requires_name_and_accepts_missing_optional_contacts(self):
        with self.assertRaises(ValidationError):
            Customer.objects.create(display_name="No Store")
        for display_name in (None, "   "):
            with self.subTest(display_name=display_name), self.assertRaises(
                ValidationError
            ):
                self.create_customer(display_name=display_name)
        with self.assertRaises(ValidationError):
            self.create_customer(email="not-an-email")

        customer = self.create_customer(
            display_name="No Contact", phone="   ", email=None
        )
        self.assertIsNone(customer.phone)
        self.assertIsNone(customer.email)

    def test_customers_are_isolated_by_store_and_duplicate_contacts_are_allowed(self):
        first = self.create_customer()
        duplicate = self.create_customer(display_name="Duplicate Contact")
        foreign = self.create_customer(
            store=self.graph_b.store,
            display_name="Foreign Customer",
        )

        self.assertCountEqual(
            self.graph_a.store.customers.values_list("pk", flat=True),
            [first.pk, duplicate.pk],
        )
        self.assertEqual(
            list(self.graph_b.store.customers.values_list("pk", flat=True)),
            [foreign.pk],
        )

    def test_store_deletion_is_protected_while_customer_exists(self):
        self.create_customer()

        with self.assertRaises(ProtectedError):
            self.graph_a.store.delete()
