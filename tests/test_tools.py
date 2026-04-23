from agent.config import AgentConfig
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
