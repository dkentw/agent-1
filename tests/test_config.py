from agent.config import AgentConfig, config_from_mapping, load_config


def test_missing_config_uses_safe_defaults(tmp_path):
    config = load_config(tmp_path / "missing.yaml")

    assert isinstance(config, AgentConfig)
    assert config.permissions.shell.default == "ask"
    assert config.permissions.filesystem.read == "allow"
    assert config.permissions.filesystem.write == "ask"
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
                "shell": {"default": "deny"},
                "network": {"default": "deny"},
            },
            "memory": {"auto_write": False},
            "models": {"default": "gpt-5.4", "remote_calls_enabled": True},
            "security": {"redact_network": False},
        }
    )

    assert config.permissions.shell.default == "deny"
    assert config.permissions.shell.read_only == "allow"
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
    assert config.permissions.credential_access == "deny"
    assert config.memory.auto_write is False
    assert config.models.default == "gpt-5.4"
    assert config.security.unknown_risk == "high"
