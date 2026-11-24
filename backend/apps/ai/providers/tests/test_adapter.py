from decimal import Decimal
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.ai.providers.adapter import (
    AssistantCostLimitExceeded,
    AssistantProviderUnavailable,
    BackendOnlyLLMAdapter,
    ProviderDraft,
    ProviderTransportError,
)
from apps.ai.providers.configuration import (
    LLMConfigurationError,
    LLMProviderPolicy,
    load_llm_provider_policy,
)


class BackendOnlyLLMAdapterTests(SimpleTestCase):
    def test_current_environment_policy_is_disabled_with_zero_cost(self):
        policy = load_llm_provider_policy({"LLM_PROVIDER": "disabled"})

        self.assertFalse(policy.execution_enabled)
        self.assertIsNone(policy.provider_name)
        self.assertIsNone(policy.model_name)
        self.assertEqual(policy.request_timeout_seconds, 0)
        self.assertEqual(policy.maximum_request_cost_bdt, Decimal("0.00"))

    def test_unapproved_provider_configuration_fails_without_disclosing_key(self):
        secret = "not-a-real-provider-key"

        with self.assertRaises(LLMConfigurationError) as raised:
            load_llm_provider_policy(
                {
                    "LLM_PROVIDER": "unapproved-provider",
                    "LLM_MODEL": "unapproved-model",
                    "LLM_API_KEY": secret,
                }
            )

        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn("unapproved-provider", str(raised.exception))

    def test_disabled_policy_never_touches_transport(self):
        transport = Mock()
        adapter = BackendOnlyLLMAdapter(
            policy=load_llm_provider_policy({}),
            transport=transport,
        )

        with self.assertRaisesRegex(
            AssistantProviderUnavailable, "Assistant generation is unavailable"
        ):
            adapter.generate_draft(
                context=Mock(),
                estimated_request_cost_bdt=Decimal("0.00"),
            )

        transport.generate.assert_not_called()

    def test_transport_timeout_is_sanitized_and_receives_configured_timeout(self):
        secret = "not-a-real-provider-key"
        transport = Mock()
        transport.generate.side_effect = ProviderTransportError(secret)
        adapter = BackendOnlyLLMAdapter(
            policy=self.enabled_test_policy(),
            transport=transport,
        )

        with self.assertRaises(AssistantProviderUnavailable) as raised:
            adapter.generate_draft(
                context=Mock(),
                estimated_request_cost_bdt=Decimal("0.25"),
            )

        self.assertEqual(str(raised.exception), "Assistant generation is temporarily unavailable.")
        self.assertNotIn(secret, str(raised.exception))
        self.assertEqual(transport.generate.call_args.kwargs["timeout_seconds"], 4)

    def test_request_over_cost_cap_does_not_call_transport(self):
        transport = Mock(return_value=ProviderDraft(text="unused", model_name="test"))
        adapter = BackendOnlyLLMAdapter(
            policy=self.enabled_test_policy(),
            transport=transport,
        )

        with self.assertRaises(AssistantCostLimitExceeded):
            adapter.generate_draft(
                context=Mock(),
                estimated_request_cost_bdt=Decimal("1.01"),
            )

        transport.generate.assert_not_called()

    @staticmethod
    def enabled_test_policy() -> LLMProviderPolicy:
        """Test-only synthetic policy; production config cannot create this state."""

        return LLMProviderPolicy(
            provider_name="test-only",
            model_name="test-only-model",
            execution_enabled=True,
            request_timeout_seconds=4,
            maximum_request_cost_bdt=Decimal("1.00"),
        )
