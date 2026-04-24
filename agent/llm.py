"""LLM adapter interface and provider-backed model service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent.config import AgentConfig
from agent.sensitive_data import redact_sensitive_data


class LLMError(RuntimeError):
    """Base exception for provider-backed model failures."""


class LLMConfigurationError(LLMError):
    """Raised when model configuration is incomplete or disabled."""


@dataclass(frozen=True)
class LLMRequest:
    model: str
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.2
    max_output_tokens: int = 400


@dataclass(frozen=True)
class LLMResponse:
    provider: str
    model: str
    text: str
    response_id: str = ""


class LLMAdapter(Protocol):
    provider: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        ...


class OpenAIResponsesAdapter:
    provider = "openai"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model,
            "input": self._build_input(request),
            "max_output_tokens": request.max_output_tokens,
        }
        raw = self._post_json(f"{self.base_url}/responses", payload)
        return LLMResponse(
            provider=self.provider,
            model=request.model,
            text=self._extract_text(raw),
            response_id=str(raw.get("id", "")),
        )

    def _build_input(self, request: LLMRequest) -> list[dict[str, object]]:
        if request.system_prompt:
            return [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": request.system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.prompt}],
                },
            ]
        return [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": request.prompt}],
            }
        ]

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"OpenAI API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise LLMError(f"OpenAI API connection failed: {exc.reason}") from exc

    def _extract_text(self, payload: dict[str, object]) -> str:
        output = payload.get("output")
        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "output_text":
                        text = block.get("text")
                        if isinstance(text, str):
                            chunks.append(text)
            if chunks:
                return "\n".join(chunk for chunk in chunks if chunk)
        if isinstance(payload.get("output_text"), str):
            return str(payload["output_text"])
        raise LLMError("OpenAI API response did not include output text.")


class ModelService:
    def __init__(self, config: AgentConfig):
        self.config = config

    def build_adapter(self, provider: str | None = None) -> LLMAdapter:
        resolved_provider = provider or self.config.models.provider
        if not self.config.models.remote_calls_enabled:
            raise LLMConfigurationError("Remote model calls are disabled. Set models.remote_calls_enabled to true.")
        api_key = os.getenv(self.config.models.api_key_env_var, "").strip()
        if not api_key:
            raise LLMConfigurationError(
                f"Missing API key environment variable: {self.config.models.api_key_env_var}"
            )
        if resolved_provider == "openai":
            return OpenAIResponsesAdapter(api_key=api_key)
        raise LLMConfigurationError(f"Unsupported model provider: {resolved_provider}")

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        system_prompt: str = "",
        api_key_override: str | None = None,
    ) -> LLMResponse:
        cleaned_prompt = redact_sensitive_data(prompt) if self.config.security.redact_model_calls else prompt
        cleaned_system_prompt = (
            redact_sensitive_data(system_prompt) if self.config.security.redact_model_calls else system_prompt
        )
        adapter = self.build_adapter_with_override(api_key_override)
        return adapter.generate(
            LLMRequest(
                model=model,
                prompt=cleaned_prompt,
                system_prompt=cleaned_system_prompt,
            )
        )

    def build_adapter_with_override(self, api_key_override: str | None) -> LLMAdapter:
        if api_key_override:
            if self.config.models.provider == "openai":
                return OpenAIResponsesAdapter(api_key=api_key_override)
            raise LLMConfigurationError(f"Unsupported model provider: {self.config.models.provider}")
        return self.build_adapter()
