"""Server-side resolution of an account's single authorized store."""
from apps.accounts.models import Account, Store, StoreMembership


def get_authorized_store(account: Account) -> Store | None:
    """Return the owner's store or an active staff store; never trust client scope."""

    owner_store = Store.objects.filter(owner=account).first()
    if owner_store is not None:
        return owner_store

    membership = (
        StoreMembership.objects.select_related("store")
        .filter(account=account, is_active=True)
        .first()
    )
    return membership.store if membership is not None else None
