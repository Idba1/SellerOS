"""Token lifecycle helper shared by registration and login."""
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.accounts.models import Account


def rotate_token(account: Account) -> Token:
    """Issue one bearer token and invalidate that account's previous token."""

    with transaction.atomic():
        locked_account = Account.objects.select_for_update().get(pk=account.pk)
        Token.objects.filter(user=locked_account).delete()
        return Token.objects.create(user=locked_account)
