"""Compact, traceable context for a future seller-reviewed reply draft.

This module is deliberately provider-free. It converts only the retrieval
service's authorized, message-relevant facts into a narrow context object with
source metadata. It does not look up customers, conversations, or unrelated
catalogue records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from apps.accounts.models import Account

from .retrieval import ProductStockFact, retrieve_relevant_product_stock_facts


_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.IGNORECASE)
_BANGLADESH_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?88)?01[3-9]\d{8}(?!\w)")


@dataclass(frozen=True)
class FactSource:
    """One record and timestamp supporting a context claim."""

    source_type: str
    source_id: UUID
    as_of: datetime


@dataclass(frozen=True)
class AssistantContextFact:
    """A customer-safe catalogue fact with its server-side evidence."""

    product_name: str
    variant_name: str | None
    selling_price: Decimal
    currency_code: str
    product_is_active: bool
    variant_is_active: bool | None
    availability: str
    sources: tuple[FactSource, ...]


@dataclass(frozen=True)
class AssistantReplyContext:
    """The full, minimized context permitted for a future draft request.

    ``message_for_provider`` is an in-memory, basic-redaction result only. It
    is not a guarantee that all personal information has been removed. A later
    provider integration must still enforce the separate privacy-transfer gate.
    """

    message_for_provider: str
    contact_identifiers_redacted: bool
    facts: tuple[AssistantContextFact, ...]


def build_assistant_reply_context(
    account: Account, *, customer_message: str
) -> AssistantReplyContext:
    """Build minimal context using only facts authorized for ``account``.

    Retrieval resolves the store from the account before querying data, so this
    builder never accepts a store selector and cannot include a foreign record.
    The original message is used only for local relevance matching; the returned
    context contains its basic-redacted form instead.
    """

    facts = retrieve_relevant_product_stock_facts(
        account,
        customer_message=customer_message,
    )
    message_for_provider, contact_identifiers_redacted = _redact_contact_identifiers(
        customer_message
    )
    return AssistantReplyContext(
        message_for_provider=message_for_provider,
        contact_identifiers_redacted=contact_identifiers_redacted,
        facts=tuple(_build_context_fact(fact) for fact in facts),
    )


def _redact_contact_identifiers(message: str) -> tuple[str, bool]:
    """Remove common email and Bangladesh phone values without claiming completeness."""

    redacted_message, email_count = _EMAIL_PATTERN.subn("[email removed]", message)
    redacted_message, phone_count = _BANGLADESH_PHONE_PATTERN.subn(
        "[phone removed]", redacted_message
    )
    return redacted_message, bool(email_count or phone_count)


def _build_context_fact(fact: ProductStockFact) -> AssistantContextFact:
    sources = [
        FactSource(
            source_type="product",
            source_id=fact.product_id,
            as_of=fact.product_updated_at,
        ),
        FactSource(
            source_type="stock_unit",
            source_id=fact.stock_unit_id,
            as_of=fact.stock_updated_at,
        ),
    ]
    if fact.variant_id is not None and fact.variant_updated_at is not None:
        sources.append(
            FactSource(
                source_type="product_variant",
                source_id=fact.variant_id,
                as_of=fact.variant_updated_at,
            )
        )
    return AssistantContextFact(
        product_name=fact.product_name,
        variant_name=fact.variant_name,
        selling_price=fact.selling_price,
        currency_code=fact.currency_code,
        product_is_active=fact.product_is_active,
        variant_is_active=fact.variant_is_active,
        availability=fact.availability,
        sources=tuple(sources),
    )
