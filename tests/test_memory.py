from agent.memory import MemoryService


def test_memory_service_create_list_get_delete(tmp_path):
    service = MemoryService(tmp_path / "memory.sqlite")
    created = service.create(
        type="project_fact",
        scope="workspace",
        content="Use uv for tests",
        summary="Use uv for tests",
        source_task_id="task_1",
        tags=("python", "tests"),
    )

    listed = service.list()
    fetched = service.get(created.id)

    assert listed
    assert listed[0].id == created.id
    assert fetched is not None
    assert fetched.summary == "Use uv for tests"
    assert service.delete(created.id) is True
    assert service.get(created.id) is None


def test_memory_service_search_and_mark_used(tmp_path):
    service = MemoryService(tmp_path / "memory.sqlite")
    created = service.create(
        type="project_fact",
        scope="workspace",
        content="Use uv run --extra dev pytest",
        summary="Use uv for pytest",
    )

    results = service.search("pytest")
    service.mark_used([created.id])
    updated = service.get(created.id)

    assert results
    assert results[0].id == created.id
    assert updated is not None
    assert updated.use_count == 1


def test_memory_service_create_or_update_and_feedback(tmp_path):
    service = MemoryService(tmp_path / "memory.sqlite")
    created = service.create_or_update(
        type="project_fact",
        scope="workspace",
        content="Use uv run --extra dev pytest",
        summary="Use uv for pytest",
        confidence=0.6,
        reliability_score=0.6,
        tags=("tests",),
    )
    updated = service.create_or_update(
        type="project_fact",
        scope="workspace",
        content="Use uv run --extra dev pytest",
        summary="Use uv for pytest",
        confidence=0.8,
        reliability_score=0.75,
        tags=("python",),
    )
    after_feedback = service.apply_feedback([updated.id], positive=False)[0]

    assert created.id == updated.id
    assert set(updated.tags) == {"tests", "python"}
    assert updated.confidence == 0.8
    assert after_feedback.confidence < updated.confidence
