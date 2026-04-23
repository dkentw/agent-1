from pathlib import Path

from agent.cli import main
from agent.memory import MemoryService


def test_config_show_command(capsys):
    exit_code = main(["--config", "does-not-exist.yaml", "config", "show"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "permissions:" in captured.out
    assert "credential_access: deny" in captured.out
    assert "unknown_risk: high" in captured.out


def test_run_command_is_available(capsys):
    exit_code = main(["--config", "does-not-exist.yaml", "run", "summarize this repo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Task received. Agent execution starts in Phase 4" in captured.out
    assert "Log:" in captured.out


def test_memory_cli_commands(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = MemoryService(Path("data/memory.sqlite"))
    created = service.create(
        type="project_fact",
        scope="workspace",
        content="Use uv for tests",
        summary="Use uv for tests",
    )

    assert main(["memory", "list"]) == 0
    listed = capsys.readouterr().out
    assert created.id in listed

    assert main(["memory", "search", "uv"]) == 0
    searched = capsys.readouterr().out
    assert created.id in searched

    assert main(["memory", "show", created.id]) == 0
    shown = capsys.readouterr().out
    assert "summary: Use uv for tests" in shown

    assert main(["memory", "delete", created.id]) == 0
    deleted = capsys.readouterr().out
    assert f"Deleted memory: {created.id}" in deleted


def test_feedback_cli_commands(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = MemoryService(Path("data/memory.sqlite"))
    created = service.create(
        type="project_fact",
        scope="workspace",
        content="Use uv for tests",
        summary="Use uv for tests",
        confidence=0.5,
        reliability_score=0.5,
    )

    assert main(["feedback", "good", "useful in practice"]) == 0
    captured = capsys.readouterr().out
    updated = service.get(created.id)

    assert "Applied good feedback to 1 memory item(s)" in captured
    assert updated is not None
    assert updated.confidence > 0.5
