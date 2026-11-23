from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.accounts.models import Account


class AuthenticationApiTests(APITestCase):
    registration_payload = {
        "email": "owner@example.test",
        "password": "synthetic registration passphrase 123!",
    }

    def create_account(self, email="owner@example.test"):
        return Account.objects.create_user(
            email, "synthetic registration passphrase 123!"
        )

    def test_registration_creates_normalized_account_and_issues_token(self):
        response = self.client.post(
            reverse("auth-register"),
            {**self.registration_payload, "email": "Owner@Example.TEST"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["account"]["email"], "owner@example.test")
        self.assertIn("token", response.data)
        account = Account.objects.get(email="owner@example.test")
        self.assertTrue(account.check_password(self.registration_payload["password"]))
        self.assertEqual(Token.objects.get(user=account).key, response.data["token"])

    def test_duplicate_registration_uses_validation_error_contract(self):
        self.create_account()

        response = self.client.post(
            reverse("auth-register"),
            {**self.registration_payload, "email": "OWNER@example.test"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("email", response.data["error"]["details"])

    def test_login_rotates_token_for_valid_credentials(self):
        account = self.create_account()
        previous = Token.objects.create(user=account)

        response = self.client.post(
            reverse("auth-login"), self.registration_payload, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["token"], previous.key)
        self.assertEqual(Token.objects.filter(user=account).count(), 1)
        self.assertEqual(Token.objects.get(user=account).key, response.data["token"])

    def test_invalid_credentials_do_not_disclose_account_existence(self):
        self.create_account()

        valid_email_wrong_password = self.client.post(
            reverse("auth-login"),
            {**self.registration_payload, "password": "wrong synthetic password"},
            format="json",
        )
        missing_email = self.client.post(
            reverse("auth-login"),
            {**self.registration_payload, "email": "missing@example.test"},
            format="json",
        )

        for response in (valid_email_wrong_password, missing_email):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.data["error"]["code"], "authentication_failed")
            self.assertEqual(
                response.data["error"]["details"]["detail"],
                "Unable to log in with provided credentials.",
            )

    def test_token_authentication_validates_current_account_and_rejects_anonymous(self):
        anonymous = self.client.get(reverse("auth-current-account"))
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(anonymous.data["error"]["code"], "not_authenticated")

        account = self.create_account()
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        authenticated = self.client.get(reverse("auth-current-account"))

        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.data["id"], str(account.id))
        self.assertEqual(authenticated.data["email"], account.email)

    def test_password_validation_rejects_short_registration_password(self):
        response = self.client.post(
            reverse("auth-register"),
            {"email": "weak@example.test", "password": "short"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("password", response.data["error"]["details"])
