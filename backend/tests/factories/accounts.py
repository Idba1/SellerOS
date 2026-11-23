"""Deterministic synthetic factories for the implemented account/store graph."""
from __future__ import annotations

from dataclasses import dataclass, field

from apps.accounts.models import Account, Store, StoreMembership

SYNTHETIC_TEST_PASSWORD = "synthetic-test-password-not-a-real-credential"


@dataclass
class FactoryContext:
    """Per-test deterministic sequence state; never use random or real data."""

    namespace: str = "fixture"
    _counters: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def next_token(self, kind: str) -> str:
        current = self._counters.get(kind, 0) + 1
        self._counters[kind] = current
        return f"{self.namespace}-{kind}-{current:03d}"


@dataclass(frozen=True)
class StoreGraph:
    """A valid same-store owner/store and optional active staff relationship."""

    owner: Account
    store: Store
    staff: Account | None
    staff_membership: StoreMembership | None


def create_account(
    context: FactoryContext,
    *,
    email: str | None = None,
    is_active: bool = True,
) -> Account:
    """Create one synthetic password-backed account with a reproducible email."""

    generated_email = f"{context.next_token('account')}@example.test"
    selected_email = email or generated_email
    if not selected_email.lower().endswith("@example.test"):
        raise ValueError("Shared factories accept only synthetic @example.test emails.")
    return Account.objects.create_user(
        selected_email,
        SYNTHETIC_TEST_PASSWORD,
        is_active=is_active,
    )


def create_store(
    context: FactoryContext,
    *,
    owner: Account | None = None,
    name: str | None = None,
) -> Store:
    """Create a BDT/Asia-Dhaka store owned by a synthetic account."""

    generated_owner = owner or create_account(context)
    generated_name = name or f"{context.next_token('store')} Store"
    return Store.objects.create(owner=generated_owner, name=generated_name)


def create_staff_membership(
    context: FactoryContext,
    *,
    store: Store,
    account: Account | None = None,
    is_active: bool = True,
) -> StoreMembership:
    """Attach one synthetic staff account to the supplied store."""

    generated_account = account or create_account(context)
    return StoreMembership.objects.create(
        store=store,
        account=generated_account,
        is_active=is_active,
    )


def create_store_graph(
    context: FactoryContext,
    *,
    include_staff: bool = True,
    staff_active: bool = True,
) -> StoreGraph:
    """Create the smallest valid store-owned graph for a feature test."""

    owner = create_account(context)
    store = create_store(context, owner=owner)
    if not include_staff:
        return StoreGraph(
            owner=owner,
            store=store,
            staff=None,
            staff_membership=None,
        )

    membership = create_staff_membership(context, store=store, is_active=staff_active)
    return StoreGraph(
        owner=owner,
        store=store,
        staff=membership.account,
        staff_membership=membership,
    )
