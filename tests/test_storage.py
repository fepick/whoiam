import sqlite3
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_ciphertext_lock_and_atomic_rollback(store: EncryptedStore) -> None:
    repository = store.scope("sample")
    repository.put({"id": "a", "note": "synthetic-secret-123"})
    assert b"synthetic-secret-123" not in Path(store.path).read_bytes()
    with pytest.raises(DomainError):
        with store.transaction():
            repository.put({"id": "a", "note": "changed"})
            raise DomainError("synthetic failure")
    assert repository.get("a")["note"] == "synthetic-secret-123"
    store.lock()
    with pytest.raises(DomainError, match="잠금"):
        repository.all()
    store.unlock()
    assert repository.get("a")["note"] == "synthetic-secret-123"


def test_reopen_tampering_and_row_binding(store: EncryptedStore) -> None:
    repository = store.scope("sample")
    repository.put({"id": "a", "note": "synthetic"})
    connection = sqlite3.connect(store.path)
    connection.execute("UPDATE records SET id='b' WHERE module='sample'")
    connection.commit()
    with pytest.raises(DomainError, match="암호문"):
        repository.get("b")
    connection.close()
    wrong = EncryptedStore(store.path, Fernet.generate_key)
    with pytest.raises(DomainError, match="키"):
        wrong.unlock()
    wrong.close()


def test_encrypted_backup_reopens_with_separate_key(
    store: EncryptedStore, tmp_path: Path
) -> None:
    store.scope("sample").put({"id": "a", "note": "synthetic-recovery-data"})
    backup = tmp_path / "synthetic-backup.sqlite3"
    connection = sqlite3.connect(backup)
    store.connection.backup(connection)
    connection.close()
    assert b"synthetic-recovery-data" not in backup.read_bytes()
    restored = EncryptedStore(backup, store.key_loader)
    restored.unlock()
    assert restored.scope("sample").get("a")["note"] == "synthetic-recovery-data"
    restored.close()
