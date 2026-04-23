"""Tool registry, routing, and approval checks."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from agent.config import AgentConfig
from agent.permissions import build_approval_request, classify_risk, decide_permission
from agent.tool_models import ApprovalRequest, ToolRequest, ToolResult
from agent.tools.filesystem import list_directory, preview_write, read_file, stat_path, write_file
from agent.tools.git import git_diff, git_status


ToolHandler = Callable[[Path, dict[str, object]], dict[str, object]]


class ToolRouter:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.handlers: dict[str, ToolHandler] = {
            "filesystem.read": lambda workspace, args: read_file(workspace, str(args["path"])),
            "filesystem.list": lambda workspace, args: list_directory(workspace, str(args.get("path", "."))),
            "filesystem.stat": lambda workspace, args: stat_path(workspace, str(args["path"])),
            "filesystem.write": lambda workspace, args: write_file(workspace, str(args["path"]), str(args["content"])),
            "git.status": lambda workspace, args: git_status(workspace),
            "git.diff": lambda workspace, args: git_diff(workspace),
        }

    def create_request(
        self,
        tool_name: str,
        args: dict[str, object],
        reason: str,
        workspace_path: Path,
        step_id: str | None = None,
    ) -> ToolRequest:
        risk_level = classify_risk(tool_name, args)
        return ToolRequest(
            tool_name=tool_name,
            args={**args, "__step_id": step_id} if step_id else args,
            reason=reason,
            workspace_path=workspace_path,
            risk_level=risk_level,
            step_id=step_id,
        )

    def route(self, request: ToolRequest) -> ToolResult | ApprovalRequest:
        if request.tool_name == "filesystem.write":
            preview = preview_write(
                request.workspace_path,
                str(request.args["path"]),
                str(request.args["content"]),
            )
            request.args["__preview_diff"] = str(preview["artifacts"]["diff"])
            request.args["__previous_content"] = str(preview["artifacts"]["previous_content"])

        decision = decide_permission(self.config, request)
        if decision.action != "allow":
            return build_approval_request(request)
        return self.execute(request)

    def execute(self, request: ToolRequest) -> ToolResult:
        if request.tool_name not in self.handlers:
            raise KeyError(f"unknown tool: {request.tool_name}")

        started_at = _utc_now_iso()
        raw = self.handlers[request.tool_name](request.workspace_path, request.args)
        finished_at = _utc_now_iso()
        return ToolResult(
            tool_name=request.tool_name,
            input=request.args,
            status="success" if not raw.get("stderr") else "error",
            stdout=str(raw.get("stdout", "")),
            stderr=str(raw.get("stderr", "")),
            artifacts=dict(raw.get("artifacts", {})),
            started_at=started_at,
            finished_at=finished_at,
            risk_level=request.risk_level,
            requires_approval=request.risk_level != "low",
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
