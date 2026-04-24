from agent.credentials import CredentialStore


def test_credential_store_hashes_pin_and_unlocks_secret(tmp_path):
    store = CredentialStore(tmp_path / "credentials.sqlite")
    record = store.store_credential("openai", "sk-live-secret", "1234")
    unlocked = store.unlock_credential("openai", "1234")

    assert store.has_pin() is True
    assert store.verify_pin("1234") is True
    assert unlocked == "sk-live-secret"
    assert store.has_credential("openai") is True


def test_credential_store_rejects_bad_pin(tmp_path):
    store = CredentialStore(tmp_path / "credentials.sqlite")
    store.store_credential("openai", "sk-live-secret", "1234")

    try:
        store.unlock_credential("openai", "9999")
    except ValueError as exc:
        assert "Invalid PIN" in str(exc)
    else:
        assert False, "expected invalid pin failure"


def test_credential_store_uses_one_pin_for_multiple_credentials(tmp_path):
    store = CredentialStore(tmp_path / "credentials.sqlite")
    store.store_credential("openai", "sk-live-secret", "1234")
    store.store_credential("anthropic", "sk-anthropic-secret", "1234")

    assert store.unlock_credential("openai", "1234") == "sk-live-secret"
    assert store.unlock_credential("anthropic", "1234") == "sk-anthropic-secret"

    try:
        store.store_credential("other", "secret", "9999")
    except ValueError as exc:
        assert "Invalid PIN" in str(exc)
    else:
        assert False, "expected invalid pin when reusing credential store"
