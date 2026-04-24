from agent.heartbeat import HeartbeatEvent
from agent.rendering import Renderer
from agent.style import strip_ansi


def test_render_heartbeat_shows_compact_progress_details():
    renderer = Renderer(color=True)
    event = HeartbeatEvent(
        session_id="session_123",
        task_id="task_123",
        loop_state="executing_tool",
        active_step_title="Run tests",
        active_tool="shell.run",
        started_at="2026-04-24T00:00:00+00:00",
        elapsed_ms=1200,
        cancellable=True,
        cancellation_requested=False,
        message="running shell.run",
        log_to_file=False,
        unhealthy=False,
    )

    rendered = strip_ansi(renderer.render_heartbeat(event))

    assert rendered == "heartbeat running Run tests | shell | 1.2s | /cancel"


def test_render_heartbeat_marks_stopping_and_stalled_states():
    renderer = Renderer(color=True)
    event = HeartbeatEvent(
        session_id="session_123",
        task_id="task_123",
        loop_state="executing_tool",
        active_step_title="Run tests",
        active_tool="shell.run",
        started_at="2026-04-24T00:00:00+00:00",
        elapsed_ms=16000,
        cancellable=True,
        cancellation_requested=True,
        message="running shell.run",
        log_to_file=True,
        unhealthy=True,
    )

    rendered = strip_ansi(renderer.render_heartbeat(event))

    assert "heartbeat running" in rendered
    assert "Run tests | shell | 16s | /cancel | stopping | stalled" in rendered
