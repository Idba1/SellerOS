"""Server-scoped catalogue facts for future customer-reply drafting.

This module deliberately performs no model/provider call and has no external
side effects. It returns only the minimum current product, variant, price, and
availability facts from the authenticated user's one authorized store.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.db.models.functions import Lower
from rest_framework.exceptions import NotFound

from apps.accounts.models import Account
from apps.inventory.models import StockUnit
from core.permissions import require_authorized_store


MAX_CUSTOMER_MESSAGE_LENGTH = 2_000
AVAILABILITY_AVAILABLE = "available"
AVAILABILITY_UNAVAILABLE = "unavailable"


class AssistantRetrievalError(ValueError):
    """Raised when a future assistant request has no valid message input."""


@dataclass(frozen=True)
class ProductStockFact:
    """Minimum current same-store fact available to a future draft workflow.

    Exact stock counts, cost, thresholds, customer data, and store identifiers
    are deliberately absent. A later draft layer can therefore communicate only
    the availability state unless a separately approved contract expands it.
    """

    stock_unit_id: UUID
    product_id: UUID
    product_name: str
    variant_id: UUID | None
    variant_name: str | None
    selling_price: Decimal
    currency_code: str
    product_is_active: bool
    variant_is_active: bool | None
    availability: str
    product_updated_at: datetime
    variant_updated_at: datetime | None
    stock_updated_at: datetime


def retrieve_relevant_product_stock_facts(
    account: Account, *, customer_message: str
) -> tuple[ProductStockFact, ...]:
    """Return only named catalogue matches in the account's authorized store.

    Matching is intentionally conservative and deterministic: the normalized
    full product name or variant name must appear in the seller-entered message.
    An unknown or partial description returns no fact rather than a guessed
    product. Store scope is resolved server-side before any catalogue records are
    queried; callers cannot select a store.
    """

    normalized_message = _validate_customer_message(customer_message)
    store = require_authorized_store(account)
    stock_units = (
        StockUnit.objects.filter(store=store)
        .select_related("product", "variant")
        .order_by(Lower("product__name").asc(), Lower("variant__name").asc(), "id")
    )
    return tuple(
        _as_product_stock_fact(stock_unit, store.currency_code)
        for stock_unit in stock_units
        if _matches_message(stock_unit, normalized_message)
    )


def retrieve_product_stock_fact(
    account: Account, *, stock_unit_id: UUID
) -> ProductStockFact:
    """Return one selected fact only when it belongs to the authorized store.

    A foreign or absent identifier has the same not-found response, preventing
    the caller from learning whether another store owns that stock record.
    """

    store = require_authorized_store(account)
    try:
        stock_unit = StockUnit.objects.select_related("product", "variant").get(
            pk=stock_unit_id,
            store=store,
        )
    except StockUnit.DoesNotExist as error:
        raise NotFound("No matching catalogue stock record was found.") from error
    return _as_product_stock_fact(stock_unit, store.currency_code)


def _validate_customer_message(customer_message: str) -> str:
    if not isinstance(customer_message, str):
        raise AssistantRetrievalError("Customer message must be plain text.")
    normalized_message = " ".join(customer_message.split()).casefold()
    if not normalized_message:
        raise AssistantRetrievalError("Customer message cannot be blank.")
    if len(normalized_message) > MAX_CUSTOMER_MESSAGE_LENGTH:
        raise AssistantRetrievalError(
            f"Customer message must be at most {MAX_CUSTOMER_MESSAGE_LENGTH} characters."
        )
    return normalized_message


def _matches_message(stock_unit: StockUnit, normalized_message: str) -> bool:
    product_name = stock_unit.product.name.casefold()
    variant_name = stock_unit.variant.name.casefold() if stock_unit.variant else None
    return product_name in normalized_message or (
        variant_name is not None and variant_name in normalized_message
    )


def _as_product_stock_fact(stock_unit: StockUnit, currency_code: str) -> ProductStockFact:
    variant = stock_unit.variant
    return ProductStockFact(
        stock_unit_id=stock_unit.pk,
        product_id=stock_unit.product_id,
        product_name=stock_unit.product.name,
        variant_id=stock_unit.variant_id,
        variant_name=variant.name if variant else None,
        selling_price=stock_unit.product.selling_price,
        currency_code=currency_code,
        product_is_active=stock_unit.product.is_active,
        variant_is_active=variant.is_active if variant else None,
        availability=(
            AVAILABILITY_AVAILABLE
            if stock_unit.quantity_on_hand > 0
            else AVAILABILITY_UNAVAILABLE
        ),
        product_updated_at=stock_unit.product.updated_at,
        variant_updated_at=variant.updated_at if variant else None,
        stock_updated_at=stock_unit.updated_at,
    )
