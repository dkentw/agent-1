from io import StringIO
from pathlib import Path

from agent.config import AgentConfig
from agent.llm import LLMResponse
from agent.logging import SessionLogger
from agent.memory import MemoryService
from agent.repl import Repl, run_repl
from agent.heartbeat import HeartbeatEvent
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
    assert "/setup-pin" in rendered
    assert "/status" in rendered
    assert "/plan" in rendered
    assert "/feedback" in rendered
    assert "/history" in rendered
    assert "/model" in rendered
    assert "/cancel" in rendered
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
    assert "provider  openai" in rendered
    assert "model  gpt-5.4-mini" in rendered
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


def test_history_command_shows_recent_inputs(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.handle_line("/status")
    repl.handle_line("/model")
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/history")

    rendered = strip_ansi(output.getvalue())
    assert "History" in rendered
    assert "/status" in rendered
    assert "/model" in rendered


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


def test_model_command_shows_active_model(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/model")

    rendered = strip_ansi(output.getvalue())
    assert "Model" in rendered
    assert "active  gpt-5.4-mini" in rendered


def test_model_command_can_switch_active_model(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/model gpt-5.4")

    rendered = strip_ansi(output.getvalue())
    assert "model set to gpt-5.4." in rendered
    assert repl.session.selected_model == "gpt-5.4"


def test_model_use_command_can_switch_active_model(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/model use gpt-5.4")

    rendered = strip_ansi(output.getvalue())
    assert "model set to gpt-5.4." in rendered
    assert repl.session.selected_model == "gpt-5.4"


def test_model_test_command_reports_config_error_when_disabled(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/model test hello")

    rendered = strip_ansi(output.getvalue())
    assert "Remote model calls are disabled" in rendered


def test_model_key_setup_stores_hashed_pin_and_unlocks_key(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/setup-pin")
    repl.handle_line("1234")
    repl.handle_line("1234")
    repl.handle_line("/model key setup")
    repl.handle_line("sk-live-secret")
    repl.handle_line("1234")

    record = repl.credential_store.get("openai")
    rendered = strip_ansi(output.getvalue())
    assert record is not None
    assert repl.credential_store.has_pin() is True
    assert repl.credential_store.verify_pin("1234") is True
    assert repl.unlocked_model_api_key == "sk-live-secret"
    assert "stored and unlocked" in rendered
    log_text = repl.session.log_path.read_text(encoding="utf-8")
    assert "sk-live-secret" not in log_text
    assert '"1234"' not in log_text


def test_setup_pin_configures_global_pin_without_storing_credential(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/setup-pin")
    repl.handle_line("1234")
    repl.handle_line("1234")

    rendered = strip_ansi(output.getvalue())
    assert repl.credential_store.has_pin() is True
    assert repl.credential_store.verify_pin("1234") is True
    assert repl.credential_store.has_credential("openai") is False
    assert "PIN configured." in rendered
    log_text = repl.session.log_path.read_text(encoding="utf-8")
    assert '"1234"' not in log_text


def test_model_key_setup_requires_pin_setup_first(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/model key setup")

    rendered = strip_ansi(output.getvalue())
    assert "PIN not configured." in rendered
    assert "/setup-pin" in rendered
    assert repl.secure_prompt_state is None


def test_model_key_unlock_uses_stored_credential(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.credential_store.store_credential("openai", "sk-live-secret", "1234")

    repl.handle_line("/model key unlock")
    repl.handle_line("1234")

    rendered = strip_ansi(output.getvalue())
    assert repl.unlocked_model_api_key == "sk-live-secret"
    assert "credential unlocked." in rendered


def test_model_key_clear_removes_stored_credential(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.credential_store.store_credential("openai", "sk-live-secret", "1234")

    repl.handle_line("/model key clear")

    rendered = strip_ansi(output.getvalue())
    assert repl.credential_store.has_credential("openai") is False
    assert "credential cleared." in rendered


def test_model_key_setup_reuses_global_pin_for_new_credential(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.credential_store.set_pin("1234")
    repl.session.model_provider = "anthropic"

    repl.handle_line("/model key setup")
    repl.handle_line("sk-anthropic-secret")
    repl.handle_line("1234")

    rendered = strip_ansi(output.getvalue())
    assert repl.credential_store.unlock_credential("anthropic", "1234") == "sk-anthropic-secret"
    assert "stored and unlocked" in rendered


def test_model_test_command_renders_provider_response(tmp_path, monkeypatch):
    repl, output = make_repl(tmp_path)

    def fake_generate(*, model, prompt, system_prompt="", api_key_override=None):
        return LLMResponse(provider="openai", model=model, text="ready", response_id="resp_123")

    monkeypatch.setattr(repl.model_service, "generate", fake_generate)

    repl.handle_line("/model test hello")

    rendered = strip_ansi(output.getvalue())
    assert "model openai/gpt-5.4-mini" in rendered
    assert "ready" in rendered


def test_model_test_command_uses_unlocked_api_key_override(tmp_path, monkeypatch):
    repl, output = make_repl(tmp_path)
    repl.unlocked_model_api_key = "sk-unlocked"

    captured = {}

    def fake_generate(*, model, prompt, system_prompt="", api_key_override=None):
        captured["api_key_override"] = api_key_override
        return LLMResponse(provider="openai", model=model, text="ready", response_id="resp_123")

    monkeypatch.setattr(repl.model_service, "generate", fake_generate)

    repl.handle_line("/model test hello")

    assert captured["api_key_override"] == "sk-unlocked"


def test_unknown_command_suggests_similar_command(tmp_path):
    repl, output = make_repl(tmp_path)

    repl.handle_line("/stats")

    rendered = strip_ansi(output.getvalue())
    assert "Did you mean /status?" in rendered


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
    assert "read README.md success" in rendered
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


def test_run_repl_supports_multiline_input():
    output = StringIO()
    prompts = []
    inputs = iter(['write "README.md" "line 1\\', 'line 2"', "/exit"])

    def input_func(prompt):
        prompts.append(strip_ansi(prompt))
        return next(inputs)

    exit_code = run_repl(AgentConfig(), input_func=input_func, output=output, color=True)

    assert exit_code == 0
    assert "... " in prompts
    rendered = strip_ansi(output.getvalue())
    assert "Write README.md" in rendered
    assert "Approval required" in rendered


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
    assert "read README.md success" in rendered
    assert "Summary" in rendered
    assert "Completed 1/1 planned step(s)." in rendered
    assert repl.session.current_plan is not None
    assert repl.session.current_plan.status == "completed"
    assert repl.session.loop_state == "completed"
    assert repl.session.learned_memories
    assert repl.session.latest_heartbeat is not None
    assert repl.session.latest_heartbeat.loop_state == "completed"


def test_follow_up_read_uses_last_active_path(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('read "README.md"')
    output.truncate(0)
    output.seek(0)

    repl.handle_line("read it again")

    rendered = strip_ansi(output.getvalue())
    assert "Read README.md" in rendered
    assert repl.session.references.last_active_path == "README.md"


def test_follow_up_run_that_test_again_uses_last_test_command(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.session.references.last_test_command = "uv run --extra dev pytest"

    repl.handle_line("run that test again")

    rendered = strip_ansi(output.getvalue())
    assert "Run tests" in rendered
    assert "Approval required" in rendered


def test_follow_up_run_that_command_again_uses_last_shell_command(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.session.references.last_shell_command = "echo hello"

    repl.handle_line("run that command again")

    rendered = strip_ansi(output.getvalue())
    assert "Run echo hello" in rendered
    assert "Approval required" in rendered


def test_follow_up_open_that_again_uses_last_active_path(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.session.references.last_active_path = "README.md"

    repl.handle_line("open that again")

    rendered = strip_ansi(output.getvalue())
    assert "Read README.md" in rendered


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


def test_follow_up_show_diff_uses_last_applied_edit(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('write "README.md" "new\\n"')
    repl.handle_line("/approve")
    output.truncate(0)
    output.seek(0)

    repl.handle_line("show the diff")

    rendered = strip_ansi(output.getvalue())
    assert "Last applied diff" in rendered
    assert "--- a/README.md" in rendered


def test_follow_up_undo_that_uses_last_applied_edit(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("old\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('write "README.md" "new\\n"')
    repl.handle_line("/approve")
    output.truncate(0)
    output.seek(0)

    repl.handle_line("undo that")

    assert readme.read_text(encoding="utf-8") == "old\n"
    assert "Undo applied." in strip_ansi(output.getvalue())


def test_follow_up_run_that_again_reuses_last_task(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    repl, output = make_repl(tmp_path)
    repl.handle_line('read "README.md"')
    output.truncate(0)
    output.seek(0)

    repl.handle_line("run that again")

    rendered = strip_ansi(output.getvalue())
    assert "read README.md success" in rendered
    assert "Completed 1/1 planned step(s)." in rendered


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
    assert "write README.md success" in rendered
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


def test_keyboard_interrupt_sets_cancellation_requested():
    output = StringIO()
    calls = {"count": 0}

    def input_func(_prompt):
        if calls["count"] == 0:
            calls["count"] += 1
            raise KeyboardInterrupt()
        raise EOFError()

    exit_code = run_repl(AgentConfig(), input_func=input_func, output=output, color=True)

    assert exit_code == 0
    rendered = strip_ansi(output.getvalue())
    assert "Cancellation requested." in rendered


def test_cancel_command_clears_pending_approval(tmp_path):
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
    output.truncate(0)
    output.seek(0)

    repl.handle_line("/cancel")

    rendered = strip_ansi(output.getvalue())
    assert "Cancelled." in rendered
    assert repl.session.pending_approval is None
    assert repl.session.pending_edit is None


def test_duplicate_heartbeat_lines_are_suppressed(tmp_path):
    repl, output = make_repl(tmp_path)
    event = HeartbeatEvent(
        session_id=repl.session.id,
        task_id="task_123",
        loop_state="executing_tool",
        active_step_title="Run tests",
        active_tool="shell.run",
        started_at="2026-04-24T00:00:00+00:00",
        elapsed_ms=1000,
        cancellable=True,
        cancellation_requested=False,
        message="running shell.run",
        log_to_file=False,
        unhealthy=False,
    )

    repl.handle_heartbeat(event)
    repl.handle_heartbeat(event)

    rendered = strip_ansi(output.getvalue()).splitlines()
    assert len(rendered) == 1
    assert rendered[0] == "heartbeat running Run tests | shell | 1.0s | /cancel"


def test_status_command_shows_heartbeat_summary(tmp_path):
    repl, output = make_repl(tmp_path)
    repl.session.latest_heartbeat = HeartbeatEvent(
        session_id=repl.session.id,
        task_id="task_123",
        loop_state="waiting_for_approval",
        active_step_title="Write README.md",
        active_tool="filesystem.write",
        started_at="2026-04-24T00:00:00+00:00",
        elapsed_ms=2000,
        cancellable=True,
        cancellation_requested=False,
        message="waiting for approval",
        log_to_file=False,
        unhealthy=False,
    )

    repl.handle_line("/status")

    rendered = strip_ansi(output.getvalue())
    assert "heartbeat  approval Write README.md | write | 2.0s | /cancel" in rendered


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
