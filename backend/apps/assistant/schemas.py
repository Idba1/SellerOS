"""Strict, evidence-bound validation for a future provider's structured reply."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from .context import AssistantContextFact, AssistantReplyContext, FactSource


ALLOWED_CLAIM_FIELDS = {"product_name", "variant_name", "price", "availability"}
CLAIM_FIELD_ORDER = ("product_name", "variant_name", "price", "availability")


@dataclass(frozen=True)
class ValidatedReply:
    """Seller-reviewable result with only source-backed statements."""

    state: str
    draft: str | None
    sources: tuple[FactSource, ...]
    warnings: tuple[str, ...]


def validate_structured_reply(
    context: AssistantReplyContext, candidate: str | Mapping[str, Any]
) -> ValidatedReply:
    """Validate provider selection and render only supported factual sentences.

    Free-text drafts are intentionally not accepted. Invalid, foreign, unknown,
    or unsupported claim selections return a safe abstention instead of an
    asserted fact. This validator sends nothing and performs no provider call.
    """

    payload = _parse_candidate(candidate)
    if payload is None:
        return _abstention("invalid_provider_output")

    if set(payload) != {"state", "claims"}:
        return _abstention("invalid_provider_output")
    state = payload.get("state")
    claims = payload.get("claims")
    if state == "abstain" and claims == []:
        return _abstention("provider_abstained")
    if state != "draft" or not isinstance(claims, list) or not claims:
        return _abstention("invalid_provider_output")

    facts_by_id = _facts_by_stock_source(context)
    selected: list[tuple[AssistantContextFact, tuple[str, ...]]] = []
    seen_fact_ids: set[UUID] = set()
    for claim in claims:
        parsed_claim = _parse_claim(claim, facts_by_id)
        if parsed_claim is None:
            return _abstention("unverified_provider_claim")
        fact_id, fact, fields = parsed_claim
        if fact_id in seen_fact_ids:
            return _abstention("invalid_provider_output")
        seen_fact_ids.add(fact_id)
        if not fact.product_is_active or fact.variant_is_active is False:
            return _abstention("inactive_catalogue_item")
        selected.append((fact, fields))

    warnings = _warnings_for(selected)
    sources = _sources_for(selected)
    return ValidatedReply(
        state="draft",
        draft=_render_draft(selected),
        sources=sources,
        warnings=warnings,
    )


def _parse_candidate(candidate: str | Mapping[str, Any]) -> Mapping[str, Any] | None:
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError:
            return None
    return candidate if isinstance(candidate, Mapping) else None


def _facts_by_stock_source(
    context: AssistantReplyContext,
) -> dict[UUID, AssistantContextFact]:
    result: dict[UUID, AssistantContextFact] = {}
    for fact in context.facts:
        for source in fact.sources:
            if source.source_type == "stock_unit":
                result[source.source_id] = fact
    return result


def _parse_claim(
    claim: Any, facts_by_id: Mapping[UUID, AssistantContextFact]
) -> tuple[UUID, AssistantContextFact, tuple[str, ...]] | None:
    if not isinstance(claim, Mapping) or set(claim) != {"fact_id", "fields"}:
        return None
    try:
        fact_id = UUID(str(claim["fact_id"]))
    except (TypeError, ValueError, AttributeError):
        return None
    fields = claim.get("fields")
    if not isinstance(fields, list) or not fields or any(
        not isinstance(field, str) for field in fields
    ):
        return None
    if len(set(fields)) != len(fields) or not set(fields).issubset(ALLOWED_CLAIM_FIELDS):
        return None
    fact = facts_by_id.get(fact_id)
    if fact is None:
        return None
    if "variant_name" in fields and fact.variant_name is None:
        return None
    return fact_id, fact, tuple(field for field in CLAIM_FIELD_ORDER if field in fields)


def _warnings_for(
    selected: list[tuple[AssistantContextFact, tuple[str, ...]]]
) -> tuple[str, ...]:
    warnings = []
    if any(fact.availability == "unavailable" for fact, _fields in selected):
        warnings.append("availability_unavailable")
    return tuple(warnings)


def _sources_for(
    selected: list[tuple[AssistantContextFact, tuple[str, ...]]]
) -> tuple[FactSource, ...]:
    required_source_types = {
        "product_name": "product",
        "variant_name": "product_variant",
        "price": "product",
        "availability": "stock_unit",
    }
    sources: list[FactSource] = []
    seen: set[tuple[str, UUID]] = set()
    for fact, fields in selected:
        for field in fields:
            source_type = required_source_types[field]
            for source in fact.sources:
                if source.source_type == source_type:
                    source_key = (source.source_type, source.source_id)
                    if source_key not in seen:
                        sources.append(source)
                        seen.add(source_key)
                    break
    return tuple(sources)


def _render_draft(selected: list[tuple[AssistantContextFact, tuple[str, ...]]]) -> str:
    sentences = ["Thanks for your message."]
    for fact, fields in selected:
        item_name = _item_name(fact)
        if "product_name" in fields:
            sentences.append(f"The product is {item_name}.")
        if "price" in fields:
            sentences.append(
                f"The current listed price for {item_name} is "
                f"{fact.currency_code} {fact.selling_price:.2f}."
            )
        if "availability" in fields:
            availability = (
                "currently available"
                if fact.availability == "available"
                else "currently unavailable"
            )
            sentences.append(f"{item_name} is {availability}.")
    sentences.append("Please review this draft before sending.")
    return " ".join(sentences)


def _item_name(fact: AssistantContextFact) -> str:
    return (
        f"{fact.product_name} ({fact.variant_name})"
        if fact.variant_name
        else fact.product_name
    )


def _abstention(warning: str) -> ValidatedReply:
    return ValidatedReply(
        state="abstain",
        draft=None,
        sources=(),
        warnings=(warning,),
    )
