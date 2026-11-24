from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from tests.factories import FactoryContext, create_store_graph


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="expenses-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="expenses-b"))

    def create_expense(self, **overrides):
        values = {
            "store": self.graph_a.store,
            "description": "  Synthetic packaging supplies  ",
            "category": "  Packaging  ",
            "amount": Decimal("125.50"),
            "incurred_on": timezone.localdate(
                timezone=ZoneInfo(self.graph_a.store.timezone)
            ),
            "recorded_by": self.graph_a.owner,
        }
        values.update(overrides)
        return Expense.objects.create(**values)

    def test_expense_is_store_owned_and_normalizes_entered_text(self):
        expense = self.create_expense()

        self.assertEqual(expense.store, self.graph_a.store)
        self.assertEqual(expense.description, "Synthetic packaging supplies")
        self.assertEqual(expense.category, "Packaging")
        self.assertEqual(expense.amount, Decimal("125.50"))
        self.assertEqual(self.graph_a.store.expenses.get(pk=expense.pk), expense)

    def test_amount_text_and_date_boundaries_are_validated(self):
        for amount in (Decimal("0.00"), Decimal("-0.01")):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.create_expense(amount=amount)
        for field in ("description", "category"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.create_expense(**{field: "   "})

        store_today = timezone.localdate(
            timezone=ZoneInfo(self.graph_a.store.timezone)
        )
        with self.assertRaises(ValidationError):
            self.create_expense(incurred_on=store_today + timedelta(days=1))

    def test_owner_or_active_same_store_staff_must_record_the_expense(self):
        staff_expense = self.create_expense(recorded_by=self.graph_a.staff)
        self.assertEqual(staff_expense.recorded_by, self.graph_a.staff)

        with self.assertRaises(ValidationError):
            self.create_expense(recorded_by=self.graph_b.owner)

        membership = self.graph_a.staff.staff_membership
        membership.is_active = False
        membership.save()
        with self.assertRaises(ValidationError):
            self.create_expense(recorded_by=self.graph_a.staff)

    def test_store_delete_is_protected_while_expense_exists(self):
        self.create_expense()

        with self.assertRaises(ProtectedError):
            self.graph_a.store.delete()
