from agent.config import AgentConfig, ConfigValidationError, config_from_mapping, load_config


def test_missing_config_uses_safe_defaults(tmp_path):
    config = load_config(tmp_path / "missing.yaml")

    assert isinstance(config, AgentConfig)
    assert config.permissions.shell.default == "ask"
    assert config.permissions.filesystem.read == "allow"
    assert config.permissions.filesystem.write == "ask"
    assert config.permissions.shell.timeout_seconds == 30
    assert config.permissions.credential_access == "deny"
    assert config.security.unknown_risk == "high"
    assert config.memory.block_secrets is True
    assert config.models.provider == "openai"
    assert config.models.default == "gpt-5.4-mini"
    assert config.models.remote_calls_enabled is False


def test_config_from_mapping_overrides_defaults():
    config = config_from_mapping(
        {
            "permissions": {
                "shell": {"default": "deny", "timeout_seconds": 45},
                "network": {"default": "deny"},
            },
            "memory": {"auto_write": False},
            "models": {"default": "gpt-5.4", "remote_calls_enabled": True},
            "security": {"redact_network": False},
        }
    )

    assert config.permissions.shell.default == "deny"
    assert config.permissions.shell.read_only == "allow"
    assert config.permissions.shell.timeout_seconds == 45
    assert config.permissions.network.default == "deny"
    assert config.memory.auto_write is False
    assert config.models.default == "gpt-5.4"
    assert config.models.remote_calls_enabled is True
    assert config.security.redact_network is False


def test_load_config_reads_workspace_file(tmp_path):
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
permissions:
  shell:
    default: deny
    timeout_seconds: 60
  credential_access: deny
memory:
  auto_write: false
models:
  default: gpt-5.4
security:
  unknown_risk: high
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.permissions.shell.default == "deny"
    assert config.permissions.shell.timeout_seconds == 60
    assert config.permissions.credential_access == "deny"
    assert config.memory.auto_write is False
    assert config.models.default == "gpt-5.4"
    assert config.security.unknown_risk == "high"


def test_config_rejects_invalid_policy_value():
    try:
        config_from_mapping({"permissions": {"filesystem": {"write": "always"}}})
    except ConfigValidationError as error:
        assert "filesystem.write must be one of" in str(error)
    else:
        raise AssertionError("expected invalid policy to fail")


def test_config_rejects_invalid_boolean_value():
    try:
        config_from_mapping({"memory": {"auto_write": "sometimes"}})
    except ConfigValidationError as error:
        assert "auto_write must be a boolean" in str(error)
    else:
        raise AssertionError("expected invalid boolean to fail")


def test_config_rejects_invalid_shell_timeout():
    try:
        config_from_mapping({"permissions": {"shell": {"timeout_seconds": 0}}})
    except ConfigValidationError as error:
        assert "shell.timeout_seconds must be between 1 and 3600" in str(error)
    else:
        raise AssertionError("expected invalid timeout to fail")


def test_config_rejects_non_mapping_sections():
    try:
        config_from_mapping({"permissions": {"shell": "ask"}})
    except ConfigValidationError as error:
        assert "permissions.shell must be a mapping" in str(error)
    else:
        raise AssertionError("expected invalid section to fail")
