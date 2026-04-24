from pathlib import Path

from agent.loop import AgentLoop
from agent.memory import MemoryService
from agent.session import create_session
from agent.tool_router import ToolRouter
from agent.config import AgentConfig


def test_loop_creates_plan_and_completes_read_only_task(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    session = create_session(workspace_path=tmp_path, sessions_dir=tmp_path / "sessions")
    loop = AgentLoop(ToolRouter(AgentConfig()), MemoryService(tmp_path / "memory.sqlite"))
    events = {"plans": [], "tools": [], "summaries": [], "states": [], "approvals": [], "heartbeats": [], "memories": []}

    result = loop.run_task(
        session=session,
        task_input='read "README.md"',
        on_plan=events["plans"].append,
        on_tool_result=events["tools"].append,
        on_approval=events["approvals"].append,
        on_summary=events["summaries"].append,
        on_state_change=events["states"].append,
        on_heartbeat=events["heartbeats"].append,
        on_memories_loaded=events["memories"].append,
        on_memories_learned=events["memories"].append,
    )

    assert result.completed is True
    assert not events["approvals"]
    assert session.current_plan is not None
    assert session.current_plan.status == "completed"
    assert len(session.current_plan.steps) == 1
    assert session.current_plan.steps[0].tool_name == "filesystem.read"
    assert events["tools"][0].stdout == "hello\n"
    assert events["summaries"][-1] == "Completed 1/1 planned step(s)."
    assert events["states"][-1] == "completed"
    assert events["heartbeats"]
    assert events["heartbeats"][0].loop_state == "loading_context"
    assert events["heartbeats"][-1].loop_state == "completed"
    assert session.learned_memories


def test_loop_stops_when_cancellation_requested(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    session = create_session(workspace_path=tmp_path, sessions_dir=tmp_path / "sessions")
    loop = AgentLoop(ToolRouter(AgentConfig()), MemoryService(tmp_path / "memory.sqlite"))
    events = {"plans": [], "tools": [], "summaries": [], "states": [], "approvals": [], "heartbeats": [], "memories": []}

    result = loop.run_task(
        session=session,
        task_input='read "README.md"',
        on_plan=lambda plan: (events["plans"].append(plan), setattr(session, "cancellation_requested", True)),
        on_tool_result=events["tools"].append,
        on_approval=events["approvals"].append,
        on_summary=events["summaries"].append,
        on_state_change=events["states"].append,
        on_heartbeat=events["heartbeats"].append,
        on_memories_loaded=events["memories"].append,
        on_memories_learned=events["memories"].append,
    )

    assert result.completed is False
    assert result.summary == "Task cancelled."
    assert not events["tools"]
    assert events["states"][-1] == "cancelled"
