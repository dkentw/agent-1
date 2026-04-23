"""Rule-based task planning for the early agent loop."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent.workspace import WorkspaceContext


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class TaskRequest:
    input: str
    mode: str
    workspace_path: Path
    id: str = field(default_factory=lambda: f"task_{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class PlanStep:
    title: str
    rationale: str
    tool_name: str
    args: dict[str, object]
    risk_level: str = "low"
    status: str = "pending"
    id: str = field(default_factory=lambda: f"step_{uuid4().hex[:12]}")


@dataclass
class Plan:
    task: str
    steps: list[PlanStep]
    status: str = "pending"
    id: str = field(default_factory=lambda: f"plan_{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


class Planner:
    def create_plan(self, task: TaskRequest, workspace: WorkspaceContext | None) -> Plan:
        lower = task.input.lower().strip()
        steps: list[PlanStep]

        if "git status" in lower:
            steps = [self._git_status_step()]
        elif "git diff" in lower or lower == "diff":
            steps = [self._git_diff_step()]
        elif write_match := self._match_write_request(task.input):
            path, content = write_match
            steps = [self._write_file_step(path, content)]
        elif match := self._match_read_request(task.input):
            steps = [self._read_file_step(match)]
        elif any(token in lower for token in ("list files", "show files", "list repo", "show repo files")):
            steps = [self._list_files_step()]
        else:
            steps = [self._list_files_step()]
            if workspace and workspace.git.is_repo:
                steps.append(self._git_status_step())

        return Plan(task=task.input, steps=steps)

    def _match_read_request(self, text: str) -> str | None:
        stripped = text.strip()
        quoted = re.search(r'read\s+"([^"]+)"', stripped, re.IGNORECASE)
        if quoted:
            return quoted.group(1)

        simple = re.search(r"read\s+([^\s]+)", stripped, re.IGNORECASE)
        if simple:
            return simple.group(1)

        if "readme" in stripped.lower():
            return "README.md"
        return None

    def _match_write_request(self, text: str) -> tuple[str, str] | None:
        quoted = re.search(r'write\s+"([^"]+)"\s+"([\s\S]+)"', text, re.IGNORECASE)
        if quoted:
            return quoted.group(1), quoted.group(2)
        return None

    def _list_files_step(self) -> PlanStep:
        return PlanStep(
            title="List workspace files",
            rationale="Inspect the workspace before taking action.",
            tool_name="filesystem.list",
            args={"path": "."},
        )

    def _git_status_step(self) -> PlanStep:
        return PlanStep(
            title="Check git status",
            rationale="Inspect repository state and uncommitted changes.",
            tool_name="git.status",
            args={},
        )

    def _git_diff_step(self) -> PlanStep:
        return PlanStep(
            title="Show git diff",
            rationale="Inspect repository changes in detail.",
            tool_name="git.diff",
            args={},
        )

    def _read_file_step(self, path: str) -> PlanStep:
        return PlanStep(
            title=f"Read {path}",
            rationale="Inspect the requested file.",
            tool_name="filesystem.read",
            args={"path": path},
        )

    def _write_file_step(self, path: str, content: str) -> PlanStep:
        return PlanStep(
            title=f"Write {path}",
            rationale="Apply the requested file update.",
            tool_name="filesystem.write",
            args={"path": path, "content": content},
            risk_level="medium",
        )
