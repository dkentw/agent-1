"""Configuration loading for the self-learning agent.

Phase 0 intentionally uses only the Python standard library. The parser below
supports the small YAML subset used by the default `agent.yaml`; it can be
replaced by a full YAML/Pydantic stack in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = "agent.yaml"


@dataclass(frozen=True)
class ShellPermissions:
    default: str = "ask"
    read_only: str = "allow"


@dataclass(frozen=True)
class FilesystemPermissions:
    read: str = "allow"
    write: str = "ask"
    delete: str = "ask"


@dataclass(frozen=True)
class NetworkPermissions:
    default: str = "ask"


@dataclass(frozen=True)
class PermissionsConfig:
    shell: ShellPermissions = field(default_factory=ShellPermissions)
    filesystem: FilesystemPermissions = field(default_factory=FilesystemPermissions)
    network: NetworkPermissions = field(default_factory=NetworkPermissions)
    high_privilege: str = "ask"
    credential_access: str = "deny"


@dataclass(frozen=True)
class MemoryConfig:
    auto_write: bool = True
    require_review_for_user_preferences: bool = True
    block_secrets: bool = True


@dataclass(frozen=True)
class SecurityConfig:
    redact_logs: bool = True
    redact_memory: bool = True
    redact_model_calls: bool = True
    redact_network: bool = True
    unknown_risk: str = "high"


@dataclass(frozen=True)
class AgentConfig:
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AgentConfig:
    """Load agent configuration from a local YAML-like file.

    Missing config files are allowed and return safe defaults.
    """

    config_path = Path(path)
    if not config_path.exists():
        return AgentConfig()

    parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    return config_from_mapping(parsed)


def config_from_mapping(raw: dict[str, Any]) -> AgentConfig:
    permissions = raw.get("permissions", {})
    memory = raw.get("memory", {})
    security = raw.get("security", {})

    return AgentConfig(
        permissions=PermissionsConfig(
            shell=ShellPermissions(
                default=_string_at(permissions, ("shell", "default"), "ask"),
                read_only=_string_at(permissions, ("shell", "read_only"), "allow"),
            ),
            filesystem=FilesystemPermissions(
                read=_string_at(permissions, ("filesystem", "read"), "allow"),
                write=_string_at(permissions, ("filesystem", "write"), "ask"),
                delete=_string_at(permissions, ("filesystem", "delete"), "ask"),
            ),
            network=NetworkPermissions(
                default=_string_at(permissions, ("network", "default"), "ask"),
            ),
            high_privilege=_string_at(permissions, ("high_privilege",), "ask"),
            credential_access=_string_at(permissions, ("credential_access",), "deny"),
        ),
        memory=MemoryConfig(
            auto_write=_bool_at(memory, ("auto_write",), True),
            require_review_for_user_preferences=_bool_at(
                memory,
                ("require_review_for_user_preferences",),
                True,
            ),
            block_secrets=_bool_at(memory, ("block_secrets",), True),
        ),
        security=SecurityConfig(
            redact_logs=_bool_at(security, ("redact_logs",), True),
            redact_memory=_bool_at(security, ("redact_memory",), True),
            redact_model_calls=_bool_at(security, ("redact_model_calls",), True),
            redact_network=_bool_at(security, ("redact_network",), True),
            unknown_risk=_string_at(security, ("unknown_risk",), "high"),
        ),
    )


def _string_at(raw: dict[str, Any], path: tuple[str, ...], default: str) -> str:
    value = _value_at(raw, path, default)
    return str(value)


def _bool_at(raw: dict[str, Any], path: tuple[str, ...], default: bool) -> bool:
    value = _value_at(raw, path, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "yes", "on", "1"}
    return bool(value)


def _value_at(raw: dict[str, Any], path: tuple[str, ...], default: Any) -> Any:
    cursor: Any = raw
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return default
        cursor = cursor[key]
    return cursor


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for original_line in text.splitlines():
        if not original_line.strip() or original_line.lstrip().startswith("#"):
            continue

        indent = len(original_line) - len(original_line.lstrip(" "))
        line = original_line.strip()
        if ":" not in line:
            raise ValueError(f"Invalid config line: {original_line}")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw_value)

    return root


def _parse_scalar(value: str) -> str | bool | int:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.isdigit():
        return int(value)
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value

