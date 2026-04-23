from io import StringIO
from pathlib import Path

from agent.config import AgentConfig
from agent.logging import SessionLogger
from agent.memory import MemoryService
from agent.repl import Repl, run_repl
from agent.session import create_session
from agent.tool_router import ToolRouter
from agent.style import strip_ansi


def make_repl(tmp_path):
    MemoryService(tmp_path / "data" / "memory.sqlite")
    session = create_session(
        workspace_path=tmp_path,
        sessions_dir=tmp_path / "sessions",
    )
    output = StringIO()
    repl = Repl(
        config=AgentConfig(),
        session=session,
        logger=SessionLogger(session.log_path),
        output=output,
        color=True,
    )
    return repl, output


def test_help_command_prints_available_commands(tmp_path):
    repl, output = make_repl(tmp_path)

    result = repl.handle_line("/help")

    assert result.should_exit is False
    rendered = strip_ansi(output.getvalue())
    assert "/help" in rendered
    assert "/status" in rendered
    assert "/plan" in rendered
    assert "/feedback" in rendered
    assert "/diff" in rendered
    assert "/undo" in rendered
    assert "/exit" in rendered


def test_status_command_includes_session_workspace_and_log_path(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    repl, output = make_repl(tmp_path)

    repl.handle_line("/status")

    rendered = strip_ansi(output.getvalue())
    assert "Status" in rendered
    assert repl.session.id in rendered
    assert str(repl.session.workspace_path) in rendered
    assert str(repl.session.log_path) in rendered
    assert "credential  deny" in rendered
    assert "package  uv" in rendered
    assert "languages  python" in rendered
    assert "uv run --extra dev pytest" in rendered


def test_clear_command_resets_visible_context(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.handle_line("summarize this repo")

    assert repl.session.conversation
    assert repl.session.active_task == "summarize this repo"

    repl.handle_line("/clear")

    assert repl.session.conversation == []
    assert repl.session.active_task is None
    assert "cleared" in strip_ansi(output.getvalue())


def test_exit_command_returns_exit_result_and_logs(tmp_path):
    repl, output = make_repl(tmp_path)

    result = repl.handle_line("/exit")

    assert result.should_exit is True
    assert "Session ended." in strip_ansi(output.getvalue())
    assert repl.session.log_path.exists()
    assert "session_ended" in repl.session.log_path.read_text(encoding="utf-8")


def test_logs_command_prints_log_path(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/logs")

    assert str(repl.session.log_path) in strip_ansi(output.getvalue())


def test_diff_command_reports_when_no_diff_exists(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/diff")

    assert "No diff available." in strip_ansi(output.getvalue())


def test_plan_command_reports_when_no_plan_exists(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/plan")

    assert "No active plan." in strip_ansi(output.getvalue())


def test_permissions_command_prints_current_policy(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/permissions")

    rendered = strip_ansi(output.getvalue())
    assert "Permissions" in rendered
    assert "shell" in rendered
    assert "fs.write" in rendered
    assert "high_priv" in rendered


def test_memory_command_reports_when_no_memories_loaded(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/memory")

    assert "No loaded memories." in strip_ansi(output.getvalue())


def test_memory_search_command_finds_records(tmp_path):
    service = MemoryService(tmp_path / "data" / "memory.sqlite")
    created = service.create(
        type="project_fact",
        scope="workspace",
        content="Use uv for tests",
        summary="Use uv for tests",
    )
    repl, output = make_repl(tmp_path)

    repl.handle_line("/memory search uv")

    rendered = strip_ansi(output.getvalue())
    assert "Memory search" in rendered
    assert created.id in rendered


def test_feedback_command_reports_when_no_task_memories_exist(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/feedback good useful")

    assert "No task memories available for feedback." in strip_ansi(output.getvalue())


def test_approve_executes_pending_tool_request(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    request = repl.tool_router.create_request(
        tool_name="filesystem.read",
        args={"path": "README.md"},
        reason="inspect readme",
        workspace_path=tmp_path,
    )
    approval = repl.tool_router.create_request(
        tool_name="filesystem.write",
        args={"path": "README.md", "content": "ignored"},
        reason="update readme",
        workspace_path=tmp_path,
    )
    # Reuse the real approval shape while swapping in an executable low-risk request.
    pending = repl.tool_router.route(approval)
    pending = pending.__class__(
        action_type=pending.action_type,
        command_or_path=pending.command_or_path,
        reason=pending.reason,
        risk_level=pending.risk_level,
        expected_effect=pending.expected_effect,
        choices=pending.choices,
        tool_request=request,
        id=pending.id,
        created_at=pending.created_at,
    )
    repl.prompt_approval(pending)

    repl.handle_line("/approve")

    rendered = strip_ansi(output.getvalue())
    assert "filesystem.read success" in rendered
    assert "hello" in rendered
    assert repl.session.pending_approval is None
    assert repl.session.recent_tool_results


def test_deny_clears_pending_approval(tmp_path):
    repl, output = make_repl(tmp_path)
    approval = repl.tool_router.route(
        repl.tool_router.create_request(
            tool_name="filesystem.write",
            args={"path": "README.md", "content": "hello"},
            reason="update readme",
            workspace_path=tmp_path,
        )
    )
    repl.prompt_approval(approval)

    repl.handle_line("/deny")

    assert repl.session.pending_approval is None
    assert "Denied." in strip_ansi(output.getvalue())


def test_run_repl_processes_input_until_exit():
    output = StringIO()
    prompts = []
    inputs = iter(["/status", "/exit"])

    def input_func(prompt):
        prompts.append(prompt)
        return next(inputs)

    exit_code = run_repl(AgentConfig(), input_func=input_func, output=output, color=True)

    assert exit_code == 0
    assert prompts
    assert strip_ansi(prompts[0]).endswith("> ")
    assert "\x1b[" in prompts[0]
    rendered = strip_ansi(output.getvalue())
    assert "Self-Learning Agent" in rendered
    assert "Status" in rendered
    assert "Session ended." in rendered


def test_task_input_renders_plan_and_summary(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    MemoryService(tmp_path / "data" / "memory.sqlite").create(
        type="project_fact",
        scope="workspace",
        content="README is important",
        summary="README note",
    )
    repl, output = make_repl(tmp_path)

    repl.handle_line('read "README.md"')

    rendered = strip_ansi(output.getvalue())
    assert "Plan" in rendered
    assert "Read README.md" in rendered
    assert "memory loaded 1 relevant item(s)." in rendered
    assert "learned stored" in rendered
    assert "heartbeat" in rendered
    assert "filesystem.read success" in rendered
    assert "Summary" in rendered
    assert "Completed 1/1 planned step(s)." in rendered
    assert repl.session.current_plan is not None
    assert repl.session.current_plan.status == "completed"
    assert repl.session.loop_state == "completed"
    assert repl.session.learned_memories
    assert repl.session.latest_heartbeat is not None
    assert repl.session.latest_heartbeat.loop_state == "completed"


def test_feedback_command_updates_current_task_memories(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('read "README.md"')
    learned_id = repl.session.learned_memories[0].id
    before = repl.memory_service.get(learned_id)
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/feedback good useful")

    after = repl.memory_service.get(learned_id)
    rendered = strip_ansi(output.getvalue())
    assert before is not None
    assert after is not None
    assert after.confidence > before.confidence
    assert "feedback applied to" in rendered


def test_write_task_creates_pending_edit_and_preview(tmp_path):
    (tmp_path / "README.md").write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)

    repl.handle_line('write "README.md" "new\\n"')

    rendered = strip_ansi(output.getvalue())
    assert "Plan" in rendered
    assert "Write README.md" in rendered
    assert "Approval required" in rendered
    assert "Preview diff" in rendered
    assert repl.session.pending_approval is not None
    assert repl.session.pending_edit is not None
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old\n"


def test_diff_command_shows_pending_edit(tmp_path):
    (tmp_path / "README.md").write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('write "README.md" "new\\n"')
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/diff")

    rendered = strip_ansi(output.getvalue())
    assert "Pending diff" in rendered
    assert "--- a/README.md" in rendered
    assert "+++ b/README.md" in rendered


def test_approve_applies_write_and_undo_restores_previous_content(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('write "README.md" "new\\n"')
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/approve")

    rendered = strip_ansi(output.getvalue())
    assert readme.read_text(encoding="utf-8") == "new\\n"
    assert "filesystem.write success" in rendered
    assert repl.session.pending_edit is None
    assert repl.session.last_applied_edit is not None

    output.truncate(0)
    output.seek(0)
    repl.handle_line("/diff")
    assert "Last applied diff" in strip_ansi(output.getvalue())

    output.truncate(0)
    output.seek(0)
    repl.handle_line("/undo")
    assert readme.read_text(encoding="utf-8") == "old\n"
    assert "Undo applied." in strip_ansi(output.getvalue())
    assert repl.session.last_applied_edit is None


def test_deny_write_keeps_file_unchanged(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('write "README.md" "new\\n"')

    repl.handle_line("/deny")

    assert readme.read_text(encoding="utf-8") == "old\n"
    assert repl.session.pending_edit is None


def test_plan_command_shows_current_plan(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('read "README.md"')
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/plan")

    rendered = strip_ansi(output.getvalue())
    assert "Plan" in rendered
    assert "Read README.md" in rendered
    assert "status  completed" in rendered


def test_prompt_uses_short_workspace_name(tmp_path):
    session = create_session(
        workspace_path=tmp_path / "example-project",
        sessions_dir=tmp_path / "sessions",
    )

    assert session.prompt == "example-project> "


def test_styled_prompt_uses_color_and_short_workspace_name(tmp_path):
    session = create_session(
        workspace_path=tmp_path / "example-project",
        sessions_dir=tmp_path / "sessions",
    )

    prompt = session.styled_prompt(color=True)

    assert "\x1b[" in prompt
    assert strip_ansi(prompt) == "example-project > "
