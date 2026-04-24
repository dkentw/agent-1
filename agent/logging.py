"""Append-only JSONL session logging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.sensitive_data import redact_sensitive_data
from agent.session import SessionState, utc_now_iso


class SessionLogger:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        event = {
            "type": event_type,
            "created_at": utc_now_iso(),
            "payload": _redact_payload(payload or {}),
        }
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=True, sort_keys=True))
            log_file.write("\n")


def log_session_started(logger: SessionLogger, session: SessionState) -> None:
    workspace = session.workspace_context
    logger.write(
        "session_started",
        {
            "session_id": session.id,
            "mode": session.mode,
            "workspace_path": str(session.workspace_path),
            "workspace": {
                "git": workspace.git.status_summary if workspace else "unknown",
                "package_manager": workspace.package_manager if workspace else None,
                "languages": list(workspace.languages) if workspace else [],
                "test_commands": list(workspace.test_commands) if workspace else [],
                "important_files": list(workspace.important_files) if workspace else [],
            },
        },
    )


def _redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_data(value)
    if isinstance(value, dict):
        return {key: _redact_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_payload(item) for item in value]
    return value
