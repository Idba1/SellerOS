"""Fail-closed provider policy loading without retaining provider secrets."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from django.core.exceptions import ImproperlyConfigured


class LLMConfigurationError(ImproperlyConfigured):
    """Raised without echoing any environment value or secret."""


@dataclass(frozen=True)
class LLMProviderPolicy:
    """Non-secret execution policy exposed through Django settings.

    Current PLAN-06 policy authorizes zero provider calls and zero spend. The
    policy intentionally contains no API key, endpoint, or provider SDK data.
    """

    provider_name: str | None
    model_name: str | None
    execution_enabled: bool
    request_timeout_seconds: int
    maximum_request_cost_bdt: Decimal


def load_llm_provider_policy(environment: Mapping[str, str]) -> LLMProviderPolicy:
    """Return the only currently approved policy: disabled, zero-cost execution.

    Any attempt to configure a provider/model/key or operational limit fails at
    startup. This prevents an unreviewed environment change from enabling a
    network call or billable spend and never places a credential in settings.
    """

    provider_name = environment.get("LLM_PROVIDER", "").strip().casefold()
    model_name = environment.get("LLM_MODEL", "").strip()
    api_key = environment.get("LLM_API_KEY", "").strip()
    timeout = environment.get("LLM_REQUEST_TIMEOUT_SECONDS", "").strip()
    request_cost_limit = environment.get("LLM_MAX_REQUEST_COST_BDT", "").strip()

    if provider_name not in {"", "disabled"} or any(
        (model_name, api_key, timeout, request_cost_limit)
    ):
        raise LLMConfigurationError(
            "LLM provider execution is disabled until provider, privacy, budget, "
            "and retention review are approved."
        )

    return LLMProviderPolicy(
        provider_name=None,
        model_name=None,
        execution_enabled=False,
        request_timeout_seconds=0,
        maximum_request_cost_bdt=Decimal("0.00"),
    )
