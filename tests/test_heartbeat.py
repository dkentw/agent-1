from agent.heartbeat import HeartbeatMonitor


def test_heartbeat_monitor_start_and_stop_emit_loggable_events():
    monitor = HeartbeatMonitor()

    started = monitor.start("session_1", "task_1", "loading_context", message="start")
    stopped = monitor.stop("completed", message="done")

    assert started.log_to_file is True
    assert started.loop_state == "loading_context"
    assert started.task_id == "task_1"
    assert stopped.log_to_file is True
    assert stopped.loop_state == "completed"
    assert stopped.cancellable is False


def test_heartbeat_monitor_can_become_unhealthy():
    monitor = HeartbeatMonitor(unhealthy_after_s=-1.0)
    monitor.start("session_1", "task_1", "planning")

    assert monitor.is_unhealthy() is True
