"""Local credential storage with hashed PIN verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from agent.session import utc_now_iso


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def _derive_key(pin: str, salt: bytes, length: int = 32) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 200_000, dklen=length)


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        counter_bytes = counter.to_bytes(4, "big")
        chunks.append(hashlib.sha256(key + nonce + counter_bytes).digest())
        counter += 1
    return b"".join(chunks)[:length]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


@dataclass(frozen=True)
class CredentialRecord:
    provider: str
    encrypted_secret: str
    encryption_salt: str
    nonce: str
    auth_tag: str
    created_at: str
    updated_at: str


class CredentialStore:
    def __init__(self, db_path: str | Path = "data/credentials.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS credential_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS credentials (
                    provider TEXT PRIMARY KEY,
                    encrypted_secret TEXT NOT NULL,
                    encryption_salt TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    auth_tag TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(credentials)").fetchall()}
            if "pin_hash" in columns:
                connection.execute("ALTER TABLE credentials DROP COLUMN pin_hash")
            if "pin_salt" in columns:
                connection.execute("ALTER TABLE credentials DROP COLUMN pin_salt")

    def has_credential(self, provider: str) -> bool:
        return self.get(provider) is not None

    def has_pin(self) -> bool:
        return self._get_setting("pin_hash") is not None and self._get_setting("pin_salt") is not None

    def set_pin(self, pin: str) -> None:
        salt = secrets.token_bytes(16)
        pin_hash = _derive_key(pin, salt)
        self._set_setting("pin_hash", _b64encode(pin_hash))
        self._set_setting("pin_salt", _b64encode(salt))

    def verify_pin(self, pin: str) -> bool:
        pin_hash = self._get_setting("pin_hash")
        pin_salt = self._get_setting("pin_salt")
        if pin_hash is None or pin_salt is None:
            raise ValueError("No PIN configured.")
        actual_pin_hash = _derive_key(pin, _b64decode(pin_salt))
        return hmac.compare_digest(_b64decode(pin_hash), actual_pin_hash)

    def get(self, provider: str) -> CredentialRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM credentials WHERE provider = ?",
                (provider,),
            ).fetchone()
        if row is None:
            return None
        return CredentialRecord(
            provider=row["provider"],
            encrypted_secret=row["encrypted_secret"],
            encryption_salt=row["encryption_salt"],
            nonce=row["nonce"],
            auth_tag=row["auth_tag"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def store_credential(self, provider: str, secret: str, pin: str) -> CredentialRecord:
        if not self.has_pin():
            self.set_pin(pin)
        elif not self.verify_pin(pin):
            raise ValueError("Invalid PIN.")
        encryption_salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(16)
        encryption_key = _derive_key(pin, encryption_salt)
        plaintext = secret.encode("utf-8")
        ciphertext = _xor_bytes(plaintext, _keystream(encryption_key, nonce, len(plaintext)))
        auth_tag = hmac.new(encryption_key, nonce + ciphertext, hashlib.sha256).digest()
        now = utc_now_iso()
        record = CredentialRecord(
            provider=provider,
            encrypted_secret=_b64encode(ciphertext),
            encryption_salt=_b64encode(encryption_salt),
            nonce=_b64encode(nonce),
            auth_tag=_b64encode(auth_tag),
            created_at=now,
            updated_at=now,
        )
        existing = self.get(provider)
        with self._connect() as connection:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO credentials (
                        provider, encrypted_secret,
                        encryption_salt, nonce, auth_tag, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.provider,
                        record.encrypted_secret,
                        record.encryption_salt,
                        record.nonce,
                        record.auth_tag,
                        record.created_at,
                        record.updated_at,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE credentials
                    SET encrypted_secret = ?, encryption_salt = ?, nonce = ?, auth_tag = ?, updated_at = ?
                    WHERE provider = ?
                    """,
                    (
                        record.encrypted_secret,
                        record.encryption_salt,
                        record.nonce,
                        record.auth_tag,
                        record.updated_at,
                        provider,
                    ),
                )
        return self.get(provider) or record

    def unlock_credential(self, provider: str, pin: str) -> str:
        record = self.get(provider)
        if record is None:
            raise ValueError(f"No credential stored for provider: {provider}")
        if not self.verify_pin(pin):
            raise ValueError("Invalid PIN.")

        encryption_salt = _b64decode(record.encryption_salt)
        nonce = _b64decode(record.nonce)
        ciphertext = _b64decode(record.encrypted_secret)
        auth_tag = _b64decode(record.auth_tag)
        encryption_key = _derive_key(pin, encryption_salt)
        expected_auth_tag = hmac.new(encryption_key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_auth_tag, auth_tag):
            raise ValueError("Credential integrity check failed.")
        plaintext = _xor_bytes(ciphertext, _keystream(encryption_key, nonce, len(ciphertext)))
        return plaintext.decode("utf-8")

    def delete(self, provider: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM credentials WHERE provider = ?",
                (provider,),
            )
        return cursor.rowcount > 0

    def _get_setting(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM credential_settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def _set_setting(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO credential_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
