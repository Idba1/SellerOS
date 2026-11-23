from django.test import TestCase
from rest_framework.exceptions import NotFound

from apps.accounts.models import Account, Store, StoreMembership
from core.permissions import (
    get_authorized_store,
    has_store_access,
    require_authorized_store,
    scope_to_authorized_store,
)


class StorePermissionHelperTests(TestCase):
    def create_account(self, email):
        return Account.objects.create_user(email, "synthetic permission passphrase 123!")

    def setUp(self):
        self.owner_a = self.create_account("owner-a@example.test")
        self.store_a = Store.objects.create(owner=self.owner_a, name="Store A")
        self.staff_a = self.create_account("staff-a@example.test")
        self.membership_a = StoreMembership.objects.create(
            store=self.store_a, account=self.staff_a
        )

        self.owner_b = self.create_account("owner-b@example.test")
        self.store_b = Store.objects.create(owner=self.owner_b, name="Store B")
        self.staff_b = self.create_account("staff-b@example.test")
        self.membership_b = StoreMembership.objects.create(
            store=self.store_b, account=self.staff_b
        )

    def test_resolves_owner_and_active_staff_to_only_their_store(self):
        self.assertEqual(get_authorized_store(self.owner_a), self.store_a)
        self.assertEqual(get_authorized_store(self.staff_a), self.store_a)
        self.assertTrue(has_store_access(self.staff_a, self.store_a))
        self.assertFalse(has_store_access(self.staff_a, self.store_b))

    def test_scoped_queryset_excludes_foreign_store_rows_before_filtering(self):
        scoped_memberships = scope_to_authorized_store(
            StoreMembership.objects.order_by("id"), self.owner_a
        )

        self.assertEqual(list(scoped_memberships), [self.membership_a])
        self.assertNotIn(self.membership_b, scoped_memberships)

    def test_missing_or_revoked_store_context_fails_closed(self):
        no_store = self.create_account("no-store@example.test")
        self.membership_a.is_active = False
        self.membership_a.save()

        for account in (no_store, self.staff_a):
            with self.subTest(account=account.email), self.assertRaises(NotFound):
                require_authorized_store(account)
