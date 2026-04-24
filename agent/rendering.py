"""Compact terminal rendering helpers for the REPL."""

from __future__ import annotations

from pathlib import Path

from agent.heartbeat import HeartbeatEvent
from agent.style import Style, paint
from agent.tool_models import ToolResult


class Renderer:
    def __init__(self, *, color: bool):
        self.color = color

    def render_tool_activity(self, result: ToolResult) -> list[str]:
        status_style = Style.green if result.status == "success" else Style.yellow
        lines = [
            paint(self._tool_summary(result), Style.cyan, enabled=self.color)
            + " "
            + paint(result.status, status_style, enabled=self.color)
        ]
        body = self._tool_body(result)
        if body:
            lines.append(body.rstrip())
        return lines

    def render_heartbeat(self, event: HeartbeatEvent) -> str:
        parts = [
            paint("heartbeat", Style.gray, enabled=self.color),
            paint(
                self.heartbeat_state_label(event.loop_state),
                self._heartbeat_state_style(event.loop_state, unhealthy=event.unhealthy),
                enabled=self.color,
            ),
        ]
        detail = self.describe_heartbeat(event)
        if detail:
            parts.append(detail)
        return " ".join(parts)

    def describe_heartbeat(self, event: HeartbeatEvent) -> str:
        segments: list[str] = []
        detail = event.active_step_title or event.message
        if detail:
            segments.append(detail)
        tool = self._compact_tool_name(event.active_tool)
        if tool:
            segments.append(tool)
        segments.append(self._format_elapsed(event.elapsed_ms))
        if event.cancellable and event.loop_state not in {"completed", "failed", "cancelled"}:
            segments.append("/cancel")
        if event.cancellation_requested:
            segments.append("stopping")
        if event.unhealthy:
            segments.append("stalled")
        return " | ".join(segments)

    def heartbeat_state_label(self, loop_state: str) -> str:
        return self._heartbeat_state_label(loop_state)

    def _tool_summary(self, result: ToolResult) -> str:
        path = self._compact_path(result.input.get("path") or result.artifacts.get("path"))
        if result.tool_name == "filesystem.read" and path:
            return f"read {path}"
        if result.tool_name == "filesystem.list":
            return f"list {path or '.'}"
        if result.tool_name == "filesystem.write" and path:
            return f"write {path}"
        if result.tool_name == "shell.run":
            command = result.input.get("command")
            if isinstance(command, str):
                return f"shell {command}"
        if result.tool_name == "git.status":
            return "git status"
        if result.tool_name == "git.diff":
            return "git diff"
        return result.tool_name

    def _tool_body(self, result: ToolResult) -> str:
        if result.stdout:
            return result.stdout
        if result.tool_name == "filesystem.write":
            diff = result.artifacts.get("diff")
            if isinstance(diff, str) and diff:
                return diff
        return ""

    def _compact_path(self, value: object) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        return Path(value).name if Path(value).is_absolute() else value

    def _compact_tool_name(self, tool_name: str | None) -> str | None:
        if not tool_name:
            return None
        if tool_name == "filesystem.read":
            return "read"
        if tool_name == "filesystem.write":
            return "write"
        if tool_name == "filesystem.list":
            return "list"
        if tool_name == "shell.run":
            return "shell"
        if tool_name == "git.status":
            return "git status"
        if tool_name == "git.diff":
            return "git diff"
        return tool_name

    def _format_elapsed(self, elapsed_ms: int) -> str:
        if elapsed_ms < 1000:
            return f"{elapsed_ms}ms"
        seconds = elapsed_ms / 1000
        if seconds < 10:
            return f"{seconds:.1f}s"
        return f"{int(seconds)}s"

    def _heartbeat_state_label(self, loop_state: str) -> str:
        labels = {
            "loading_context": "loading",
            "planning": "planning",
            "executing_tool": "running",
            "waiting_for_approval": "approval",
            "observing": "observing",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        return labels.get(loop_state, loop_state)

    def _heartbeat_state_style(self, loop_state: str, *, unhealthy: bool) -> str:
        if unhealthy:
            return Style.red
        if loop_state == "completed":
            return Style.green
        if loop_state in {"failed", "cancelled"}:
            return Style.yellow
        if loop_state == "waiting_for_approval":
            return Style.magenta
        return Style.cyan
