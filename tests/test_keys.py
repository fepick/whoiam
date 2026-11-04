from pathlib import Path
from typing import Any

import pytest
from cryptography.fernet import Fernet

from packages.platform import keys
from packages.platform.domain import DomainError


def test_no_plaintext_fallback_or_key_replacement(
    tmp_path: Path, monkeypatch: Any
) -> None:
    class FakeBackend:
        def __init__(self) -> None:
            self.value: str | None = None
            self.writes = 0

        def get_password(self, service: str, account: str) -> str | None:
            return self.value

        def set_password(self, service: str, account: str, value: str) -> None:
            self.value = value
            self.writes += 1

    backend = FakeBackend()
    monkeypatch.setattr(keys.keyring, "get_keyring", lambda: backend)
    with pytest.raises(DomainError, match="OS"):
        keys.os_key(tmp_path / "synthetic.sqlite3")
    FakeBackend.__module__ = "keyring.backends.Windows"
    key = keys.os_key(tmp_path / "synthetic.sqlite3")
    Fernet(key)
    assert backend.writes == 1
    existing = tmp_path / "existing.sqlite3"
    existing.touch()
    backend.value = None
    with pytest.raises(DomainError, match="새 키"):
        keys.os_key(existing)
    assert backend.writes == 1
