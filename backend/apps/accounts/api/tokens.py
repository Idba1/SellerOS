"""Token lifecycle and password-reset helpers for account access."""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.accounts.models import Account


def rotate_token(account: Account) -> Token:
    """Issue one bearer token and invalidate that account's previous token."""

    with transaction.atomic():
        locked_account = Account.objects.select_for_update().get(pk=account.pk)
        Token.objects.filter(user=locked_account).delete()
        return Token.objects.create(user=locked_account)


class AccountPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """Time-limited reset tokens for SellerOS's minimal custom account model.

    The account does not inherit Django's full ``AbstractBaseUser`` contract,
    so the hash deliberately uses only values that exist and that invalidate a
    link after a password change or account deactivation.
    """

    def _make_hash_value(self, user: Account, timestamp: int) -> str:
        return f"{user.pk}{user.password}{timestamp}{user.is_active}"


password_reset_token_generator = AccountPasswordResetTokenGenerator()
