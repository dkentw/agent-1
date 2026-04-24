"""Model registry and selection helpers."""

from __future__ import annotations

from dataclasses import dataclass

from agent.config import ModelsConfig


@dataclass(frozen=True)
class ModelInfo:
    name: str
    provider: str
    roles: tuple[str, ...]
    remote: bool = True


class ModelRegistry:
    def __init__(self):
        self._models = {
            "gpt-5.4-mini": ModelInfo(
                name="gpt-5.4-mini",
                provider="openai",
                roles=("default", "planner", "reflector"),
            ),
            "gpt-5.4": ModelInfo(
                name="gpt-5.4",
                provider="openai",
                roles=("default", "planner", "reflector"),
            ),
            "gpt-5.3-codex": ModelInfo(
                name="gpt-5.3-codex",
                provider="openai",
                roles=("coding", "planner"),
            ),
            "gpt-5.2": ModelInfo(
                name="gpt-5.2",
                provider="openai",
                roles=("default", "planner", "reflector"),
            ),
        }

    def list_models(self, provider: str | None = None) -> list[ModelInfo]:
        models = list(self._models.values())
        if provider is not None:
            models = [model for model in models if model.provider == provider]
        return sorted(models, key=lambda item: item.name)

    def get(self, name: str) -> ModelInfo | None:
        return self._models.get(name)

    def validate(self, name: str) -> bool:
        return name in self._models

    def default_model(self, config: ModelsConfig) -> ModelInfo:
        model = self.get(config.default)
        if model is not None:
            return model
        return self._models["gpt-5.4-mini"]
