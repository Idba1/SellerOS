from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AccountsMigrationSmokeTests(TransactionTestCase):
    """Exercise the accounts migration rollback/reapply path on PostgreSQL."""

    @staticmethod
    def migrate_to(target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])

    @staticmethod
    def store_constraints():
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, "accounts_store")

    def test_currency_constraint_rolls_back_and_reapplies(self):
        self.migrate_to(("accounts", "0001_initial"))
        self.assertNotIn("accounts_store_currency_bdt", self.store_constraints())

        self.migrate_to(("accounts", "0002_store_currency_bdt"))
        self.assertIn("accounts_store_currency_bdt", self.store_constraints())

        self.migrate_to(("accounts", "0001_initial"))
        self.assertNotIn("accounts_store_currency_bdt", self.store_constraints())

        self.migrate_to(("accounts", "0002_store_currency_bdt"))
        self.assertIn("accounts_store_currency_bdt", self.store_constraints())
