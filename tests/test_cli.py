from pathlib import Path

from agent.cli import main
from agent.llm import LLMResponse
from agent.memory import MemoryService


def test_config_show_command(capsys):
    exit_code = main(["--config", "does-not-exist.yaml", "config", "show"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "permissions:" in captured.out
    assert "models:" in captured.out
    assert "credential_access: deny" in captured.out
    assert "unknown_risk: high" in captured.out


def test_run_command_is_available(capsys):
    exit_code = main(["--config", "does-not-exist.yaml", "run", "summarize this repo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Task received. Agent execution starts in Phase 4" in captured.out
    assert "Model: openai/gpt-5.4-mini" in captured.out
    assert "Log:" in captured.out


def test_run_command_accepts_model_override(capsys):
    exit_code = main(["--config", "does-not-exist.yaml", "--model", "gpt-5.4", "run", "summarize this repo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Model: openai/gpt-5.4" in captured.out


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


def test_model_cli_commands(capsys):
    assert main(["model", "show"]) == 0
    shown = capsys.readouterr().out
    assert "provider: openai" in shown
    assert "default: gpt-5.4-mini" in shown

    assert main(["model", "list"]) == 0
    listed = capsys.readouterr().out
    assert "gpt-5.4-mini" in listed


def test_model_cli_test_command_uses_provider(monkeypatch, capsys):
    def fake_generate(self, *, model, prompt, system_prompt=""):
        return LLMResponse(provider="openai", model=model, text="ok", response_id="resp_test")

    monkeypatch.setattr("agent.cli.ModelService.generate", fake_generate)

    assert main(["model", "test", "hello"]) == 0
    rendered = capsys.readouterr().out
    assert "provider: openai" in rendered
    assert "model: gpt-5.4-mini" in rendered
    assert "ok" in rendered


def test_invalid_model_override_fails(capsys):
    exit_code = main(["--model", "does-not-exist", "run", "summarize this repo"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unknown model: does-not-exist" in captured.out
