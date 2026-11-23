from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Account, Store, StoreMembership


class AccountStoreDatabaseConstraintTests(TestCase):
    def create_account(self, email):
        return Account.objects.create_user(email, "strong-password-for-tests")

    def test_case_insensitive_email_unique_constraint_rejects_bulk_insert(self):
        self.create_account("seller@example.test")
        duplicate = Account(email="SELLER@example.test", password="not-a-real-hash")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Account.objects.bulk_create([duplicate])

    def test_owner_one_to_one_constraint_rejects_second_store_bypassing_clean(self):
        owner = self.create_account("owner@example.test")
        Store.objects.create(owner=owner, name="First Store")
        duplicate = Store(owner=owner, name="Second Store")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Store.objects.bulk_create([duplicate])

    def test_currency_check_constraint_rejects_direct_update(self):
        owner = self.create_account("owner@example.test")
        store = Store.objects.create(owner=owner, name="Currency Store")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Store.objects.filter(pk=store.pk).update(currency_code="USD")

    def test_staff_role_check_constraint_rejects_direct_update(self):
        owner = self.create_account("owner@example.test")
        store = Store.objects.create(owner=owner, name="Role Store")
        staff = self.create_account("staff@example.test")
        membership = StoreMembership.objects.create(store=store, account=staff)

        with self.assertRaises(IntegrityError), transaction.atomic():
            StoreMembership.objects.filter(pk=membership.pk).update(role="OWNER")
