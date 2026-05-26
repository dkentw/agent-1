from agent.config import AgentConfig, PermissionsConfig, ShellPermissions
from agent.tool_models import ApprovalRequest, ToolResult
from agent.tool_router import ToolRouter


def test_tool_router_allows_read_only_filesystem_read(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="filesystem.read",
        args={"path": "README.md"},
        reason="inspect readme",
        workspace_path=tmp_path,
    )

    result = router.route(request)

    assert isinstance(result, ToolResult)
    assert result.tool_name == "filesystem.read"
    assert result.status == "success"
    assert result.stdout == "hello\n"
    assert result.risk_level == "low"


def test_tool_router_requests_approval_for_sensitive_file_read(tmp_path):
    (tmp_path / ".env").write_text("API_KEY=sk-live-secret\n", encoding="utf-8")
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="filesystem.read",
        args={"path": ".env"},
        reason="inspect env",
        workspace_path=tmp_path,
    )

    result = router.route(request)

    assert isinstance(result, ApprovalRequest)
    assert result.risk_level == "high"
    assert result.command_or_path == ".env"


def test_tool_router_requests_approval_for_write(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="filesystem.write",
        args={"path": "README.md", "content": "hi"},
        reason="update readme",
        workspace_path=tmp_path,
    )

    result = router.route(request)

    assert isinstance(result, ApprovalRequest)
    assert result.risk_level == "medium"
    assert result.action_type == "filesystem.write"
    assert result.command_or_path == "README.md"
    assert "--- a/README.md" in result.preview_diff
    assert "+++ b/README.md" in result.preview_diff


def test_tool_router_blocks_workspace_escape(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="filesystem.read",
        args={"path": "..\\outside.txt"},
        reason="inspect outside file",
        workspace_path=tmp_path,
    )

    try:
        router.route(request)
    except PermissionError as error:
        assert "escapes workspace" in str(error)
    else:
        raise AssertionError("expected workspace escape to fail")


def test_tool_router_executes_write_when_explicitly_run(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="filesystem.write",
        args={"path": "README.md", "content": "updated\n"},
        reason="update readme",
        workspace_path=tmp_path,
    )

    result = router.execute(request)

    assert result.tool_name == "filesystem.write"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "updated\n"
    assert "--- a/README.md" in str(result.artifacts.get("diff", ""))


def test_tool_router_can_cancel_shell_command(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="shell.run",
        args={"command": 'python -c "import time; time.sleep(2)"'},
        reason="run a long shell command",
        workspace_path=tmp_path,
    )

    result = router.execute(request, is_cancelled=lambda: True)

    assert result.tool_name == "shell.run"
    assert result.status == "cancelled"
    assert result.cancelled is True


def test_tool_router_times_out_shell_command(tmp_path):
    config = AgentConfig(
        permissions=PermissionsConfig(shell=ShellPermissions(timeout_seconds=1))
    )
    router = ToolRouter(config)
    request = router.create_request(
        tool_name="shell.run",
        args={"command": 'python -c "import time; time.sleep(2)"'},
        reason="run a long shell command",
        workspace_path=tmp_path,
    )

    result = router.execute(request)

    assert result.tool_name == "shell.run"
    assert result.status == "timeout"
    assert result.artifacts["timed_out"] is True
    assert result.artifacts["timeout_seconds"] == 1


def test_tool_router_runs_shell_commands_without_shell_by_default(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="shell.run",
        args={"command": 'python -c "print(123)"'},
        reason="run a simple command",
        workspace_path=tmp_path,
    )

    result = router.execute(request)

    assert result.status == "success"
    assert result.stdout.strip() == "123"
    assert result.artifacts["use_shell"] is False


def test_tool_router_treats_explicit_shell_mode_as_high_risk(tmp_path):
    router = ToolRouter(AgentConfig())
    request = router.create_request(
        tool_name="shell.run",
        args={"command": "echo hi > out.txt", "use_shell": True},
        reason="run shell syntax",
        workspace_path=tmp_path,
    )

    result = router.route(request)

    assert isinstance(result, ApprovalRequest)
    assert result.risk_level == "high"


def test_tool_router_rejects_missing_workspace(tmp_path):
    router = ToolRouter(AgentConfig())
    missing = tmp_path / "missing"
    request = router.create_request(
        tool_name="filesystem.list",
        args={"path": "."},
        reason="list missing workspace",
        workspace_path=missing,
    )

    try:
        router.execute(request)
    except PermissionError as error:
        assert "workspace path does not exist" in str(error)
    else:
        raise AssertionError("expected missing workspace to fail")
