"""Write minimized, immutable assistant-evaluation evidence."""
from __future__ import annotations

from apps.accounts.models import Account, Store

from .context import AssistantReplyContext, FactSource
from .models import AssistantEvaluationLog


def record_assistant_evaluation(
    *,
    store: Store,
    requested_by: Account,
    customer_message_length: int,
    context: AssistantReplyContext,
    outcome_state: str,
    warning_codes: tuple[str, ...],
) -> AssistantEvaluationLog:
    """Persist reproducible fact metadata without raw customer/provider content."""

    return AssistantEvaluationLog.objects.create(
        store=store,
        requested_by=requested_by,
        outcome_state=outcome_state,
        provider_state="DISABLED",
        message_length=customer_message_length,
        contact_identifiers_redacted=context.contact_identifiers_redacted,
        context_fact_count=len(context.facts),
        source_metadata=[_source_metadata(source) for source in _unique_sources(context)],
        warning_codes=list(warning_codes),
    )


def _unique_sources(context: AssistantReplyContext) -> tuple[FactSource, ...]:
    sources: list[FactSource] = []
    seen: set[tuple[str, object]] = set()
    for fact in context.facts:
        for source in fact.sources:
            source_key = (source.source_type, source.source_id)
            if source_key not in seen:
                seen.add(source_key)
                sources.append(source)
    return tuple(sources)


def _source_metadata(source: FactSource) -> dict[str, str]:
    return {
        "source_type": source.source_type,
        "source_id": str(source.source_id),
        "as_of": source.as_of.isoformat(),
    }
