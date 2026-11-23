"""Checkpoint 02: authenticated seller onboarding and store-isolation flow."""
from django.urls import reverse
from rest_framework.test import APITestCase


class AuthenticatedStoreFlowTests(APITestCase):
    password = "Synthetic integration passphrase 123!"

    def setUp(self):
        self.register_url = reverse("auth-register")
        self.login_url = reverse("auth-login")
        self.current_account_url = reverse("auth-current-account")
        self.current_store_url = reverse("store-current-profile")

    def register(self, email):
        response = self.client.post(
            self.register_url,
            {"email": email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        return response.data

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def test_signed_in_owner_reaches_own_store_and_cannot_switch_tenants(self):
        seller_a = self.register("seller-a@example.test")
        self.authenticate(seller_a["token"])

        before_onboarding = self.client.get(self.current_store_url)
        self.assertEqual(before_onboarding.status_code, 404)
        self.assertEqual(before_onboarding.data["error"]["code"], "not_found")

        created_a = self.client.post(
            self.current_store_url,
            {"name": "Seller A Store", "timezone": "Asia/Dhaka"},
            format="json",
        )
        self.assertEqual(created_a.status_code, 201)

        self.client.credentials()
        signed_in_a = self.client.post(
            self.login_url,
            {"email": "seller-a@example.test", "password": self.password},
            format="json",
        )
        self.assertEqual(signed_in_a.status_code, 200)
        self.authenticate(signed_in_a.data["token"])

        current_account = self.client.get(self.current_account_url)
        current_store = self.client.get(self.current_store_url)
        self.assertEqual(current_account.status_code, 200)
        self.assertEqual(current_account.data["id"], seller_a["account"]["id"])
        self.assertEqual(current_store.status_code, 200)
        self.assertEqual(current_store.data, created_a.data)

        self.client.credentials()
        seller_b = self.register("seller-b@example.test")
        self.authenticate(seller_b["token"])
        created_b = self.client.post(
            self.current_store_url,
            {"name": "Seller B Store", "timezone": "Asia/Dhaka"},
            format="json",
        )
        self.assertEqual(created_b.status_code, 201)

        self.authenticate(signed_in_a.data["token"])
        own_store_after_b_onboarding = self.client.get(self.current_store_url)
        attempted_switch = self.client.get(
            f"{self.current_store_url}?store_id={created_b.data['id']}"
        )

        self.assertEqual(own_store_after_b_onboarding.status_code, 200)
        self.assertEqual(own_store_after_b_onboarding.data, created_a.data)
        self.assertEqual(attempted_switch.status_code, 400)
        self.assertEqual(attempted_switch.data["error"]["code"], "validation_error")
        self.assertEqual(
            attempted_switch.data["error"]["details"]["store_id"],
            ["Unsupported query parameter."],
        )
        self.assertNotIn(created_b.data["id"], str(attempted_switch.data))
        self.assertNotIn(created_b.data["name"], str(attempted_switch.data))
