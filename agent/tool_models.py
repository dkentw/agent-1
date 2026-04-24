"""Structured tool and approval models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    args: dict[str, Any]
    reason: str
    workspace_path: Path
    risk_level: str = "low"
    step_id: str | None = None
    id: str = field(default_factory=lambda: f"toolreq_{uuid4().hex[:12]}")


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    input: dict[str, Any]
    status: str
    stdout: str
    stderr: str
    artifacts: dict[str, Any]
    started_at: str
    finished_at: str
    risk_level: str
    requires_approval: bool
    cancelled: bool = False
    id: str = field(default_factory=lambda: f"toolres_{uuid4().hex[:12]}")


@dataclass(frozen=True)
class ApprovalRequest:
    action_type: str
    command_or_path: str
    reason: str
    risk_level: str
    expected_effect: str
    choices: tuple[str, ...]
    tool_request: ToolRequest
    preview_diff: str = ""
    id: str = field(default_factory=lambda: f"approval_{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class PendingEdit:
    path: str
    diff: str
    previous_content: str
    new_content: str
    tool_request: ToolRequest
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class AppliedEdit:
    path: str
    diff: str
    previous_content: str
    new_content: str
    applied_at: str = field(default_factory=utc_now_iso)
