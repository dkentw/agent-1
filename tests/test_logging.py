from agent.logging import SessionLogger


def test_session_logger_redacts_nested_secrets(tmp_path):
    logger = SessionLogger(tmp_path / "session.jsonl")

    logger.write(
        "tool_result",
        {
            "input": {
                "command": 'echo password=supersecret token=abcd',
                "nested": ["keep", "api_key=sk-live-secret"],
            },
            "output": "private key -----BEGIN PRIVATE KEY----- data",
        },
    )

    log_text = (tmp_path / "session.jsonl").read_text(encoding="utf-8")
    assert "supersecret" not in log_text
    assert "sk-live-secret" not in log_text
    assert "PRIVATE KEY" not in log_text
    assert "[REDACTED_SECRET]" in log_text
