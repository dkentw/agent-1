from agent.config import AgentConfig
from agent.llm import LLMConfigurationError, LLMResponse, ModelService
from agent.sensitive_data import redact_sensitive_data


def test_model_service_requires_remote_calls_enabled():
    service = ModelService(AgentConfig())

    try:
        service.build_adapter()
    except LLMConfigurationError as exc:
        assert "Remote model calls are disabled" in str(exc)
    else:
        assert False, "expected remote-calls-disabled configuration error"


def test_redact_sensitive_data_masks_tokens():
    redacted = redact_sensitive_data("token=sk-secret1234567890123456")

    assert "[REDACTED_SECRET]" in redacted
    assert "sk-secret" not in redacted
