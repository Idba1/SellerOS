from decimal import Decimal

from django.core.management import CommandError, call_command
from django.db import connection
from django.db.models import Sum
from django.test import TestCase, override_settings

from apps.accounts.models import Store
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.orders.models import OrderStatusEvent, SalesOrder


@override_settings(DEBUG=True)
class DemoSeedCommandTests(TestCase):
    def demo_metrics(self):
        return {
            "stores": Store.objects.count(),
            "products": Product.objects.count(),
            "customers": Customer.objects.count(),
            "delivered_orders": SalesOrder.objects.filter(status="DELIVERED").count(),
            "status_events": OrderStatusEvent.objects.count(),
            "expenses": Expense.objects.count(),
            "expense_total": Expense.objects.aggregate(total=Sum("amount"))["total"],
        }

    def test_reset_command_rebuilds_repeatable_supported_demo_metrics(self):
        call_command("seed_demo_data", "--reset")
        first_metrics = self.demo_metrics()

        call_command("seed_demo_data", "--reset")
        second_metrics = self.demo_metrics()

        self.assertEqual(
            first_metrics,
            {
                "stores": 2,
                "products": 5,
                "customers": 4,
                "delivered_orders": 3,
                "status_events": 12,
                "expenses": 3,
                "expense_total": Decimal("520.00"),
            },
        )
        self.assertEqual(second_metrics, first_metrics)
        self.assertTrue(
            all(
                customer.email is None and customer.phone is None
                for customer in Customer.objects.all()
            )
        )

    @override_settings(DEBUG=False)
    def test_production_guard_rejects_reset(self):
        with self.assertRaisesMessage(CommandError, "DEBUG=True"):
            call_command("seed_demo_data", "--reset")

    def test_non_test_database_guard_rejects_reset(self):
        original_name = connection.settings_dict["NAME"]
        connection.settings_dict["NAME"] = "selleros_dev"
        try:
            with self.assertRaisesMessage(CommandError, "test database"):
                call_command("seed_demo_data", "--reset")
        finally:
            connection.settings_dict["NAME"] = original_name
