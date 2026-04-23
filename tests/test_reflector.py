from agent.memory import MemoryService
from agent.planner import Plan, PlanStep
from agent.reflector import ReflectionService
from agent.workspace import detect_workspace


def test_reflection_stores_safe_workspace_facts(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    service = MemoryService(tmp_path / "memory.sqlite")
    reflector = ReflectionService()
    workspace = detect_workspace(tmp_path)
    plan = Plan(
        task='read "README.md"',
        status="completed",
        steps=[
            PlanStep(
                title="Read README.md",
                tool_name="filesystem.read",
                rationale="Inspect repo docs",
                args={"path": "README.md"},
                status="completed",
            )
        ],
    )

    stored, rejected = reflector.store_safe_proposals(
        memory_service=service,
        task_id="task_1",
        task_input='read "README.md"',
        plan=plan,
        workspace_context=workspace,
    )

    assert not rejected
    assert stored
    assert any(record.summary == "Workspace uses uv" for record in stored)
    assert any("README.md" in record.summary for record in stored)


def test_reflection_rejects_sensitive_memory_content(tmp_path):
    service = MemoryService(tmp_path / "memory.sqlite")
    reflector = ReflectionService()
    plan = Plan(
        task="inspect secret",
        status="completed",
        steps=[
            PlanStep(
                title="Read secret.txt",
                tool_name="filesystem.read",
                rationale="Inspect secret",
                args={"path": "secret.txt"},
                status="completed",
            )
        ],
    )

    stored, rejected = reflector.store_safe_proposals(
        memory_service=service,
        task_id="task_1",
        task_input="token=sk-secret1234567890123456",
        plan=plan,
        workspace_context=None,
    )

    assert not stored
    assert rejected
