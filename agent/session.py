"""Session state for interactive and one-shot agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent.heartbeat import HeartbeatEvent
from agent.memory import MemoryRecord
from agent.planner import Plan
from agent.style import Style, paint
from agent.tool_models import AppliedEdit, ApprovalRequest, PendingEdit, ToolResult
from agent.workspace import WorkspaceContext, detect_workspace


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ConversationTurn:
    role: str
    content: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class SessionState:
    id: str
    workspace_path: Path
    mode: str
    log_path: Path
    started_at: str = field(default_factory=utc_now_iso)
    active_task: str | None = None
    current_task_id: str | None = None
    loop_state: str = "idle"
    workspace_context: WorkspaceContext | None = None
    loaded_memories: list[MemoryRecord] = field(default_factory=list)
    learned_memories: list[MemoryRecord] = field(default_factory=list)
    current_plan: Plan | None = None
    pending_approval: ApprovalRequest | None = None
    pending_edit: PendingEdit | None = None
    last_applied_edit: AppliedEdit | None = None
    latest_heartbeat: HeartbeatEvent | None = None
    recent_tool_results: list[ToolResult] = field(default_factory=list)
    conversation: list[ConversationTurn] = field(default_factory=list)

    @property
    def prompt(self) -> str:
        return f"{self.workspace_name}> "

    def styled_prompt(self, color: bool = True) -> str:
        return (
            paint(self.workspace_name, Style.cyan, Style.bold, enabled=color)
            + paint(" > ", Style.gray, enabled=color)
        )

    @property
    def workspace_name(self) -> str:
        return self.workspace_path.name or str(self.workspace_path)

    def append_turn(self, role: str, content: str) -> ConversationTurn:
        turn = ConversationTurn(role=role, content=content)
        self.conversation.append(turn)
        return turn

    def clear_visible_context(self) -> None:
        self.conversation.clear()
        self.active_task = None
        self.current_task_id = None
        self.loop_state = "idle"
        self.loaded_memories = []
        self.learned_memories = []
        self.current_plan = None
        self.pending_approval = None
        self.pending_edit = None
        self.latest_heartbeat = None


def create_session(
    workspace_path: str | Path | None = None,
    mode: str = "interactive",
    sessions_dir: str | Path = "data/sessions",
) -> SessionState:
    workspace = Path(workspace_path or Path.cwd()).resolve()
    session_id = f"session_{uuid4().hex[:12]}"
    log_dir = Path(sessions_dir)
    log_path = log_dir / f"{session_id}.jsonl"
    return SessionState(
        id=session_id,
        workspace_path=workspace,
        mode=mode,
        log_path=log_path,
        workspace_context=detect_workspace(workspace),
    )
