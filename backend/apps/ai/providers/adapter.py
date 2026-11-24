"""Provider-neutral backend adapter with fail-closed controls.

There is no concrete provider implementation in SellerOS. A later, separately
approved provider module may implement ``LLMTransport``; this adapter provides
the only allowed call boundary and turns transport failures into safe public
errors without exposing transport details or secrets.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from apps.assistant.context import AssistantReplyContext

from .configuration import LLMProviderPolicy


class ProviderTransportError(RuntimeError):
    """Internal transport failure that must never be returned to a client."""


class AssistantProviderUnavailable(RuntimeError):
    """Safe public state for disabled, timed-out, or failed provider access."""


class AssistantCostLimitExceeded(RuntimeError):
    """Safe public state when a pre-approved request would exceed its cap."""


@dataclass(frozen=True)
class ProviderDraft:
    """A future provider response, still subject to seller review downstream."""

    text: str
    model_name: str


class LLMTransport(Protocol):
    """Backend-only transport contract; no browser-facing implementation exists."""

    def generate(
        self, *, context: AssistantReplyContext, timeout_seconds: int
    ) -> ProviderDraft: ...


class BackendOnlyLLMAdapter:
    """Enforce approval, timeout handoff, cost cap, and safe error translation."""

    def __init__(self, *, policy: LLMProviderPolicy, transport: LLMTransport):
        self._policy = policy
        self._transport = transport

    def generate_draft(
        self,
        *,
        context: AssistantReplyContext,
        estimated_request_cost_bdt: Decimal,
    ) -> ProviderDraft:
        """Generate only after a policy-approved future provider configuration.

        The current production policy is disabled with a zero cost cap, so this
        method exits before touching the transport. No retries or provider
        fallback are attempted; those behaviors require separate approval.
        """

        if not self._policy.execution_enabled:
            raise AssistantProviderUnavailable("Assistant generation is unavailable.")

        estimated_cost = _validate_estimated_cost(estimated_request_cost_bdt)
        if estimated_cost > self._policy.maximum_request_cost_bdt:
            raise AssistantCostLimitExceeded(
                "Assistant generation exceeds the approved request cost limit."
            )

        try:
            return self._transport.generate(
                context=context,
                timeout_seconds=self._policy.request_timeout_seconds,
            )
        except (TimeoutError, ProviderTransportError):
            raise AssistantProviderUnavailable(
                "Assistant generation is temporarily unavailable."
            ) from None


def _validate_estimated_cost(value: Decimal) -> Decimal:
    try:
        estimated_cost = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise AssistantCostLimitExceeded(
            "Assistant generation has no valid approved cost estimate."
        ) from error
    if not estimated_cost.is_finite() or estimated_cost < 0:
        raise AssistantCostLimitExceeded(
            "Assistant generation has no valid approved cost estimate."
        )
    return estimated_cost
