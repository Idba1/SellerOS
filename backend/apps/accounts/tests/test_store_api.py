from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.accounts.models import Account, Store, StoreMembership


class StoreProfileApiTests(APITestCase):
    def create_account(self, email):
        return Account.objects.create_user(
            email, "synthetic store profile passphrase 123!"
        )

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_owner_without_store_can_create_and_read_own_profile(self):
        owner = self.create_account("owner@example.test")
        self.authenticate(owner)

        created = self.client.post(
            reverse("store-current-profile"),
            {"name": "Owner Store", "timezone": "Asia/Dhaka"},
            format="json",
        )
        read = self.client.get(reverse("store-current-profile"))

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["name"], "Owner Store")
        self.assertEqual(created.data["timezone"], "Asia/Dhaka")
        self.assertEqual(created.data["currency_code"], "BDT")
        self.assertEqual(str(Store.objects.get(owner=owner).id), created.data["id"])
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data, created.data)

    def test_create_rejects_client_owned_or_unsupported_fields(self):
        owner = self.create_account("owner@example.test")
        other_account = self.create_account("other@example.test")
        self.authenticate(owner)

        response = self.client.post(
            reverse("store-current-profile"),
            {
                "name": "Safe Store",
                "owner_id": str(other_account.id),
                "currency_code": "USD",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("owner_id", response.data["error"]["details"])
        self.assertIn("currency_code", response.data["error"]["details"])
        self.assertFalse(Store.objects.exists())

    def test_owner_cannot_create_a_second_store(self):
        owner = self.create_account("owner@example.test")
        Store.objects.create(owner=owner, name="Existing Store")
        self.authenticate(owner)

        response = self.client.post(
            reverse("store-current-profile"), {"name": "Second Store"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertEqual(Store.objects.filter(owner=owner).count(), 1)

    def test_active_staff_can_read_but_cannot_create_a_store(self):
        owner = self.create_account("owner@example.test")
        store = Store.objects.create(owner=owner, name="Shared Store")
        staff = self.create_account("staff@example.test")
        StoreMembership.objects.create(store=store, account=staff)
        self.authenticate(staff)

        read = self.client.get(reverse("store-current-profile"))
        create = self.client.post(
            reverse("store-current-profile"), {"name": "Staff Store"}, format="json"
        )

        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data["id"], str(store.id))
        self.assertEqual(create.status_code, 403)
        self.assertEqual(create.data["error"]["code"], "permission_denied")
        self.assertEqual(Store.objects.count(), 1)

    def test_revoked_staff_and_account_without_store_cannot_read_profile(self):
        owner = self.create_account("owner@example.test")
        store = Store.objects.create(owner=owner, name="Revoked Store")
        revoked = self.create_account("revoked@example.test")
        StoreMembership.objects.create(store=store, account=revoked, is_active=False)
        self.authenticate(revoked)

        revoked_response = self.client.get(reverse("store-current-profile"))
        self.assertEqual(revoked_response.status_code, 404)
        self.assertEqual(revoked_response.data["error"]["code"], "not_found")

        no_store = self.create_account("no-store@example.test")
        no_store_token = Token.objects.create(user=no_store)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {no_store_token.key}")
        no_store_response = self.client.get(reverse("store-current-profile"))
        self.assertEqual(no_store_response.status_code, 404)
        self.assertEqual(no_store_response.data["error"]["code"], "not_found")

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(reverse("store-current-profile"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
