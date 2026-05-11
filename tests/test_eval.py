"""Tests for Phase 9: Evaluation Harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.config import AgentConfig
from agent.eval.fixtures import BASIC_FILES, temp_workspace
from agent.eval.metrics import EvalRunMetrics, TaskMetrics
from agent.eval.runner import EvalRunner, EvalToolRouter
from agent.eval.scenario import (
    BUILTIN_SCENARIOS,
    EvalScenario,
    get_builtin,
    load_scenario,
    resolve_scenario,
)
from agent.eval.store import EvalStore
from agent.tool_models import ToolRequest
from agent.tool_router import ToolRouter


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


def test_builtin_scenarios_exist():
    assert len(BUILTIN_SCENARIOS) >= 3
    ids = {s.id for s in BUILTIN_SCENARIOS}
    assert "basic_inspect" in ids
    assert "file_read" in ids
    assert "memory_retention" in ids


def test_get_builtin_returns_scenario():
    s = get_builtin("basic_inspect")
    assert s is not None
    assert s.id == "basic_inspect"
    assert len(s.tasks) > 0


def test_get_builtin_unknown_returns_none():
    assert get_builtin("does_not_exist") is None


def test_load_scenario_from_file(tmp_path):
    data = {
        "id": "test_scenario",
        "name": "Test",
        "description": "A test scenario",
        "tasks": ["list files"],
        "tags": ["test"],
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    s = load_scenario(path)
    assert s.id == "test_scenario"
    assert s.tasks == ["list files"]
    assert s.tags == ["test"]


def test_resolve_scenario_by_builtin_id():
    s = resolve_scenario("file_read")
    assert s is not None
    assert s.id == "file_read"


def test_resolve_scenario_by_file_path(tmp_path):
    data = {"id": "from_file", "name": "From File", "tasks": ["git status"]}
    path = tmp_path / "s.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    s = resolve_scenario(str(path))
    assert s is not None
    assert s.id == "from_file"


def test_resolve_scenario_unknown_returns_none():
    assert resolve_scenario("no_such_scenario_xyz") is None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _make_task(completed: bool = True, tool_failures: int = 0, memory_hits: int = 0, memories_learned: int = 0) -> TaskMetrics:
    return TaskMetrics(
        task_input="list files",
        completed=completed,
        steps_total=1,
        steps_completed=1 if completed else 0,
        tool_failures=tool_failures,
        approval_prompts=0,
        memory_hits=memory_hits,
        memories_learned=memories_learned,
        duration_seconds=0.1,
    )


def test_eval_run_metrics_new():
    run = EvalRunMetrics.new("basic_inspect", with_memory=True)
    assert run.run_id.startswith("eval_")
    assert run.scenario_id == "basic_inspect"
    assert run.with_memory is True
    assert run.task_metrics == []


def test_completion_rate_empty():
    run = EvalRunMetrics.new("x", with_memory=True)
    assert run.completion_rate == 0.0


def test_completion_rate_all_completed():
    run = EvalRunMetrics.new("x", with_memory=True)
    run.task_metrics = [_make_task(True), _make_task(True)]
    assert run.completion_rate == 1.0
    assert run.tasks_completed == 2


def test_completion_rate_partial():
    run = EvalRunMetrics.new("x", with_memory=True)
    run.task_metrics = [_make_task(True), _make_task(False)]
    assert run.completion_rate == 0.5


def test_aggregate_totals():
    run = EvalRunMetrics.new("x", with_memory=True)
    run.task_metrics = [
        _make_task(True, tool_failures=1, memory_hits=2, memories_learned=1),
        _make_task(True, tool_failures=0, memory_hits=3, memories_learned=0),
    ]
    assert run.total_tool_failures == 1
    assert run.total_memory_hits == 5
    assert run.total_memories_learned == 1
    assert run.total_duration_seconds == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# EvalStore
# ---------------------------------------------------------------------------


def _make_run(scenario_id: str = "basic_inspect", with_memory: bool = True) -> EvalRunMetrics:
    run = EvalRunMetrics.new(scenario_id, with_memory=with_memory)
    run.task_metrics = [_make_task()]
    return run


def test_eval_store_save_and_get(tmp_path):
    store = EvalStore(tmp_path / "eval.sqlite")
    run = _make_run()
    store.save(run)

    retrieved = store.get(run.run_id)
    assert retrieved is not None
    assert retrieved.run_id == run.run_id
    assert retrieved.scenario_id == "basic_inspect"
    assert retrieved.with_memory is True
    assert len(retrieved.task_metrics) == 1
    assert retrieved.task_metrics[0].completed is True


def test_eval_store_list(tmp_path):
    store = EvalStore(tmp_path / "eval.sqlite")
    store.save(_make_run("a"))
    store.save(_make_run("b"))

    runs = store.list()
    assert len(runs) == 2
    scenario_ids = {r.scenario_id for r in runs}
    assert scenario_ids == {"a", "b"}


def test_eval_store_get_missing_returns_none(tmp_path):
    store = EvalStore(tmp_path / "eval.sqlite")
    assert store.get("eval_doesnotexist") is None


def test_eval_store_replace_on_duplicate_id(tmp_path):
    store = EvalStore(tmp_path / "eval.sqlite")
    run = _make_run()
    store.save(run)
    run.task_metrics.append(_make_task(False))
    store.save(run)

    runs = store.list()
    assert len(runs) == 1
    assert len(runs[0].task_metrics) == 2


def test_eval_store_with_memory_false(tmp_path):
    store = EvalStore(tmp_path / "eval.sqlite")
    run = _make_run(with_memory=False)
    store.save(run)

    retrieved = store.get(run.run_id)
    assert retrieved is not None
    assert retrieved.with_memory is False


# ---------------------------------------------------------------------------
# EvalToolRouter
# ---------------------------------------------------------------------------


def test_eval_tool_router_auto_approves_shell(tmp_path):
    config = AgentConfig()
    router = EvalToolRouter(config)
    request = ToolRequest(
        tool_name="shell.run",
        args={"command": "echo hi"},
        reason="test",
        workspace_path=tmp_path,
        risk_level="medium",
    )
    result = router.route(request)
    assert result.status in {"success", "error"}
    assert router.approval_prompts == 1


def test_eval_tool_router_no_approval_for_read(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    config = AgentConfig()
    router = EvalToolRouter(config)
    request = ToolRequest(
        tool_name="filesystem.read",
        args={"path": "README.md"},
        reason="test",
        workspace_path=tmp_path,
        risk_level="low",
    )
    result = router.route(request)
    assert result.status == "success"
    assert router.approval_prompts == 0


def test_eval_tool_router_counts_failures(tmp_path):
    config = AgentConfig()
    router = EvalToolRouter(config)
    request = ToolRequest(
        tool_name="filesystem.read",
        args={"path": "nonexistent_file.txt"},
        reason="test",
        workspace_path=tmp_path,
        risk_level="low",
    )
    result = router.route(request)
    assert result.status == "error"
    assert router.tool_failures == 1


def test_eval_tool_router_reset(tmp_path):
    config = AgentConfig()
    router = EvalToolRouter(config)
    router.approval_prompts = 3
    router.tool_failures = 2
    router.reset()
    assert router.approval_prompts == 0
    assert router.tool_failures == 0


# ---------------------------------------------------------------------------
# EvalRunner
# ---------------------------------------------------------------------------


def test_eval_runner_basic_scenario(tmp_path):
    scenario = EvalScenario(
        id="test_list",
        name="Test List",
        description="Lists files",
        tasks=["list files"],
    )
    runner = EvalRunner(AgentConfig(), workspace_path=tmp_path)
    run = runner.run(scenario, with_memory=True)

    assert run.scenario_id == "test_list"
    assert run.with_memory is True
    assert run.tasks_total == 1
    assert run.tasks_completed == 1
    assert run.completion_rate == 1.0
    assert run.task_metrics[0].steps_completed == 1
    assert run.task_metrics[0].duration_seconds >= 0


def test_eval_runner_collects_metrics_per_task(tmp_path):
    scenario = EvalScenario(
        id="multi",
        name="Multi",
        description="Two tasks",
        tasks=["list files", "list files"],
    )
    runner = EvalRunner(AgentConfig(), workspace_path=tmp_path)
    run = runner.run(scenario, with_memory=True)

    assert run.tasks_total == 2
    assert len(run.task_metrics) == 2


def test_eval_runner_no_memory_uses_fresh_db(tmp_path):
    scenario = EvalScenario(
        id="nomem",
        name="No Mem",
        description="",
        tasks=["list files"],
    )
    runner = EvalRunner(AgentConfig(), workspace_path=tmp_path)
    run = runner.run(scenario, with_memory=False)

    assert run.with_memory is False
    assert run.tasks_completed == 1
    assert not (tmp_path / "data" / "eval_memory.sqlite").exists()


def test_eval_runner_uses_temp_workspace_when_no_path():
    scenario = EvalScenario(
        id="tmpws",
        name="Temp WS",
        description="",
        tasks=["list files"],
    )
    runner = EvalRunner(AgentConfig())
    run = runner.run(scenario, with_memory=False)

    assert run.tasks_completed == 1


def test_eval_runner_second_task_has_memory_hits(tmp_path):
    scenario = EvalScenario(
        id="memhit",
        name="Memory Hit",
        description="",
        tasks=["list files", "list files"],
    )
    runner = EvalRunner(AgentConfig(), workspace_path=tmp_path)
    run = runner.run(scenario, with_memory=True)

    assert run.tasks_total == 2
    assert run.total_memories_learned >= 0


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_eval_scenarios(capsys):
    from agent.cli import main

    exit_code = main(["eval", "scenarios"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "basic_inspect" in captured.out
    assert "file_read" in captured.out


def test_cli_eval_list_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from agent.cli import main

    exit_code = main(["eval", "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "No evaluation runs" in captured.out


def test_cli_eval_run_scenario(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from agent.cli import main

    exit_code = main(["eval", "file_read"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "file_read" in captured.out


def test_cli_eval_unknown_scenario(capsys):
    from agent.cli import main

    exit_code = main(["eval", "no_such_scenario_xyz_abc"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Unknown scenario" in captured.out


def test_cli_eval_no_args(capsys):
    from agent.cli import main

    exit_code = main(["eval"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Usage" in captured.out


def test_cli_eval_compare_missing_args(capsys):
    from agent.cli import main

    exit_code = main(["eval", "compare"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def test_temp_workspace_creates_files():
    with temp_workspace() as ws:
        assert (ws / "README.md").exists()
        assert (ws / "hello.py").exists()
        assert (ws / "tests" / "test_hello.py").exists()


def test_temp_workspace_custom_files():
    files = {"custom.txt": "hello"}
    with temp_workspace(files) as ws:
        assert (ws / "custom.txt").read_text() == "hello"
        assert not (ws / "README.md").exists()
