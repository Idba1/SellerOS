"""Shared server-side store-context resolution and queryset scoping."""
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound

from apps.accounts.models import Account, Store, StoreMembership


def get_authorized_store(account: Account) -> Store | None:
    """Resolve one owner's store or one active staff store without client input."""

    owner_store = Store.objects.filter(owner=account).first()
    if owner_store is not None:
        return owner_store

    membership = (
        StoreMembership.objects.select_related("store")
        .filter(account=account, is_active=True)
        .first()
    )
    return membership.store if membership is not None else None


def require_authorized_store(account: Account) -> Store:
    """Fail closed without revealing a store profile when no store is permitted."""

    store = get_authorized_store(account)
    if store is None:
        raise NotFound("No authorized store profile was found.")
    return store


def has_store_access(account: Account, store: Store) -> bool:
    """Return whether a store is the account's sole permitted store."""

    authorized_store = get_authorized_store(account)
    return authorized_store is not None and authorized_store.pk == store.pk


def scope_to_authorized_store(
    queryset: QuerySet,
    account: Account,
    *,
    store_field: str = "store",
) -> QuerySet:
    """Restrict a store-owned queryset before any filter, count, or response."""

    return queryset.filter(**{store_field: require_authorized_store(account)})
