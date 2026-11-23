from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.accounts.models import Account, Store, StoreMembership


class AccountStoreModelTests(TestCase):
    def create_account(self, email="seller@example.test"):
        return Account.objects.create_user(email, "strong-password-for-tests")

    def test_account_manager_normalizes_email_and_hashes_password(self):
        account = self.create_account("Seller@Example.TEST")

        self.assertEqual(account.email, "seller@example.test")
        self.assertNotEqual(account.password, "strong-password-for-tests")
        self.assertTrue(account.check_password("strong-password-for-tests"))

        with self.assertRaises(ValidationError):
            Account.objects.create_user("SELLER@example.test", "another-password")

    def test_owner_can_have_exactly_one_store(self):
        owner = self.create_account()
        store = Store.objects.create(owner=owner, name="Demo Store")

        self.assertEqual(store.owner, owner)
        self.assertEqual(owner.owned_store, store)

        with self.assertRaises(ValidationError):
            Store.objects.create(owner=owner, name="Second Store")

    def test_owner_and_staff_roles_are_mutually_exclusive(self):
        owner = self.create_account()
        store = Store.objects.create(owner=owner, name="Owner Store")

        with self.assertRaises(ValidationError):
            StoreMembership.objects.create(store=store, account=owner)

        staff = self.create_account("staff@example.test")
        membership = StoreMembership.objects.create(store=store, account=staff)
        self.assertTrue(membership.is_active)
        self.assertEqual(membership.role, StoreMembership.Role.STAFF)

        with self.assertRaises(ValidationError):
            Store.objects.create(owner=staff, name="Staff Store")

    def test_membership_is_single_store_and_revocation_preserves_row(self):
        owner = self.create_account()
        store = Store.objects.create(owner=owner, name="Primary Store")
        other_owner = self.create_account("other@example.test")
        other_store = Store.objects.create(owner=other_owner, name="Other Store")
        staff = self.create_account("staff@example.test")
        membership = StoreMembership.objects.create(store=store, account=staff)

        membership.is_active = False
        membership.save()
        self.assertFalse(StoreMembership.objects.get(pk=membership.pk).is_active)

        with self.assertRaises(ValidationError):
            StoreMembership.objects.create(store=other_store, account=staff)

    def test_protected_links_preserve_account_and_store_history(self):
        owner = self.create_account()
        store = Store.objects.create(owner=owner, name="Protected Store")
        staff = self.create_account("staff@example.test")
        StoreMembership.objects.create(store=store, account=staff)

        with self.assertRaises(ProtectedError):
            owner.delete()
        with self.assertRaises(ProtectedError):
            store.delete()
