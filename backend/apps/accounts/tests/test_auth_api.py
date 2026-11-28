from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.accounts.models import Account


class AuthenticationApiTests(APITestCase):
    registration_payload = {
        "email": "owner@example.test",
        "password": "synthetic registration passphrase 123!",
    }

    def setUp(self):
        super().setUp()
        cache.clear()

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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_one_time_link_and_revokes_existing_token(self):
        account = self.create_account()
        old_token = Token.objects.create(user=account)

        request_response = self.client.post(
            reverse("auth-password-reset"), {"email": account.email}, format="json"
        )

        self.assertEqual(request_response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        reset_url = next(
            line.removeprefix("Set a new password: ")
            for line in mail.outbox[0].body.splitlines()
            if line.startswith("Set a new password: ")
        )
        parsed = urlparse(reset_url)
        payload = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        payload["password"] = "new synthetic passphrase 456!"

        confirm_response = self.client.post(
            reverse("auth-password-reset-confirm"), payload, format="json"
        )

        self.assertEqual(confirm_response.status_code, 200)
        account.refresh_from_db()
        self.assertTrue(account.check_password(payload["password"]))
        self.assertFalse(Token.objects.filter(key=old_token.key).exists())
        self.assertEqual(
            self.client.post(reverse("auth-login"), {"email": account.email, "password": payload["password"]}, format="json").status_code,
            200,
        )
        replay_response = self.client.post(
            reverse("auth-password-reset-confirm"), payload, format="json"
        )
        self.assertEqual(replay_response.status_code, 400)
        self.assertEqual(replay_response.data["error"]["code"], "validation_error")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_does_not_disclose_unknown_or_inactive_account(self):
        inactive = self.create_account("inactive@example.test")
        inactive.is_active = False
        inactive.save(update_fields=["is_active", "updated_at"])

        for email in ("unknown@example.test", inactive.email):
            with self.subTest(email=email):
                response = self.client.post(
                    reverse("auth-password-reset"), {"email": email}, format="json"
                )
                self.assertEqual(response.status_code, 202)
                self.assertEqual(
                    response.data["detail"],
                    "If an active account matches this email, a reset link has been sent.",
                )
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_rejects_invalid_link(self):
        self.create_account()
        invalid_link = self.client.post(
            reverse("auth-password-reset-confirm"),
            {"uid": "not-a-valid-uid", "token": "invalid", "password": "new synthetic passphrase 456!"},
            format="json",
        )
        self.assertEqual(invalid_link.status_code, 400)
        self.assertIn("invalid or has expired", invalid_link.data["error"]["details"]["non_field_errors"][0])
