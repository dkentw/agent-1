"""Permission policy and approval decisions."""

from __future__ import annotations

from dataclasses import dataclass

from agent.config import AgentConfig
from agent.tool_models import ApprovalRequest, ToolRequest


@dataclass(frozen=True)
class PermissionDecision:
    action: str
    reason: str


def classify_risk(tool_name: str, args: dict[str, object]) -> str:
    path = _tool_path(args)
    if _looks_sensitive_path(path):
        return "high"

    if tool_name in {"filesystem.read", "filesystem.list", "filesystem.stat", "git.status", "git.diff"}:
        return "low"
    if tool_name in {"filesystem.write", "shell.run", "tests.run"}:
        return "medium"
    if tool_name in {"filesystem.delete", "network.request", "credentials.read"}:
        return "high"
    return "high"


def decide_permission(config: AgentConfig, request: ToolRequest) -> PermissionDecision:
    risk = request.risk_level
    if risk == "high":
        return PermissionDecision("ask", "high-risk action requires approval")

    if request.tool_name.startswith("filesystem."):
        operation = request.tool_name.split(".", 1)[1]
        if operation == "read":
            return PermissionDecision(config.permissions.filesystem.read, "filesystem read policy")
        if operation in {"list", "stat"}:
            return PermissionDecision(config.permissions.filesystem.read, "filesystem read policy")
        if operation == "write":
            return PermissionDecision(config.permissions.filesystem.write, "filesystem write policy")
        if operation == "delete":
            return PermissionDecision(config.permissions.filesystem.delete, "filesystem delete policy")

    if request.tool_name.startswith("git."):
        return PermissionDecision("allow", "read-only git inspection")

    if request.tool_name.startswith("shell."):
        return PermissionDecision(config.permissions.shell.default, "shell policy")

    return PermissionDecision("ask", "unknown tool defaults to approval")


def build_approval_request(request: ToolRequest) -> ApprovalRequest:
    target = str(request.args.get("path") or request.args.get("repo_path") or request.args.get("command") or request.tool_name)
    return ApprovalRequest(
        action_type=request.tool_name,
        command_or_path=target,
        reason=request.reason,
        risk_level=request.risk_level,
        expected_effect=_expected_effect(request.tool_name),
        choices=("approve once", "deny"),
        tool_request=request,
        preview_diff=str(request.args.get("__preview_diff", "")),
    )


def _expected_effect(tool_name: str) -> str:
    if tool_name.startswith("filesystem."):
        return "inspect workspace files"
    if tool_name.startswith("git."):
        return "inspect repository state"
    if tool_name.startswith("shell."):
        return "run a shell command"
    return "perform a tool action"


def _tool_path(args: dict[str, object]) -> str:
    for key in ("path", "repo_path", "command"):
        value = args.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _looks_sensitive_path(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered for token in (".env", ".pem", ".key", "id_rsa", "id_ed25519", "credentials"))
