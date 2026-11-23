"""Two-store authorization regression tests for the implemented API surface."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.accounts.models import Store, StoreMembership
from core.permissions import scope_to_authorized_store
from tests.factories import FactoryContext, create_store_graph


class StoreIsolationApiTests(APITestCase):
    """Exercise the current store API with separate synthetic seller tenants."""

    def setUp(self):
        self.store_a = create_store_graph(FactoryContext(namespace="store-a"))
        self.store_b = create_store_graph(FactoryContext(namespace="store-b"))
        self.current_store_url = reverse("store-current-profile")

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_unauthenticated_request_is_denied_without_store_disclosure(self):
        response = self.client.get(self.current_store_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
        self.assertNotIn(str(self.store_a.store.id), str(response.data))
        self.assertNotIn(str(self.store_b.store.id), str(response.data))

    def test_owner_and_active_staff_can_read_only_their_same_store(self):
        for account in (self.store_a.owner, self.store_a.staff):
            with self.subTest(account=account.email):
                self.authenticate(account)
                response = self.client.get(self.current_store_url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["id"], str(self.store_a.store.id))
                self.assertNotEqual(response.data["id"], str(self.store_b.store.id))

    def test_foreign_store_selector_is_denied_without_data_disclosure(self):
        self.authenticate(self.store_a.staff)

        response = self.client.get(
            f"{self.current_store_url}?store_id={self.store_b.store.id}"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertEqual(
            response.data["error"]["details"]["store_id"],
            ["Unsupported query parameter."],
        )
        self.assertNotIn(self.store_b.store.name, str(response.data))
        self.assertNotIn(str(self.store_b.store.id), str(response.data))

    def test_staff_cannot_create_a_store(self):
        initial_store_count = Store.objects.count()
        self.authenticate(self.store_a.staff)

        response = self.client.post(
            self.current_store_url,
            {"name": "Unauthorized Store"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "permission_denied")
        self.assertEqual(Store.objects.count(), initial_store_count)


class StoreScopedObjectLookupTests(TestCase):
    """Prove the shared queryset helper hides a foreign store-owned record."""

    def setUp(self):
        self.store_a = create_store_graph(FactoryContext(namespace="lookup-a"))
        self.store_b = create_store_graph(FactoryContext(namespace="lookup-b"))

    def test_scoped_object_lookup_allows_same_store_and_hides_foreign_store(self):
        memberships_for_a = scope_to_authorized_store(
            StoreMembership.objects.all(), self.store_a.owner
        )

        self.assertEqual(
            memberships_for_a.get(pk=self.store_a.staff_membership.pk),
            self.store_a.staff_membership,
        )
        self.assertEqual(memberships_for_a.count(), 1)
        with self.assertRaises(StoreMembership.DoesNotExist):
            memberships_for_a.get(pk=self.store_b.staff_membership.pk)
