from pathlib import Path
from typing import Iterator

import pytest

from packages.platform.backups import Backups
from packages.platform.domain import DomainError
from packages.platform.runtime import RuntimePaths
from packages.platform.storage import IDLE_SECONDS, EncryptedStore
from packages.platform.vault import Vault, VaultKeys
from tests.test_runtime import MemoryKeys


@pytest.fixture
def backup_system(tmp_path: Path) -> Iterator[tuple[EncryptedStore, Vault, Backups]]:
    vault = Vault(RuntimePaths("test", tmp_path / "synthetic"), VaultKeys(MemoryKeys()))
    store = EncryptedStore(vault.paths.database, vault.load_key)
    store.unlock()
    service = Backups(store, vault)
    yield store, vault, service
    service.stop()
    store.close()


def test_backup_restore_and_pre_restore_safety(backup_system: tuple) -> None:
    store, vault, backups = backup_system
    repository = store.scope("sample")
    repository.put({"id": "a", "note": "synthetic-before"})
    first = backups.create()
    assert b"synthetic-before" not in backups.path(first["id"]).read_bytes()
    repository.put({"id": "a", "note": "synthetic-after"})
    with pytest.raises(DomainError):
        backups.restore(first["id"], store.revision - 1)
    result = backups.restore(first["id"], store.revision)
    assert repository.get("a")["note"] == "synthetic-before"
    backups.restore(result["safety_backup"], store.revision)
    assert repository.get("a")["note"] == "synthetic-after"


def test_automatic_backup_does_not_extend_idle_and_lock_saves_changes(
    backup_system: tuple,
) -> None:
    store, vault, backups = backup_system
    store.scope("sample").put({"id": "a", "note": "synthetic"})
    touched = store.touched
    backups.safe_backup()
    assert store.touched == touched
    store.scope("sample").put({"id": "b", "note": "synthetic"})
    store.lock()
    assert store.locked
    store.unlock()
    assert len(backups.list()) == 2


def test_tampered_backup_is_rejected_before_active_database_changes(
    backup_system: tuple,
) -> None:
    store, vault, backups = backup_system
    store.scope("sample").put({"id": "a", "note": "synthetic"})
    first = backups.create()
    backups.path(first["id"]).write_bytes(b"synthetic corrupt backup")
    with pytest.raises(DomainError):
        backups.restore(first["id"], store.revision)
    assert store.scope("sample").get("a")["note"] == "synthetic"


def test_idle_expiry_saves_latest_revision_without_unlocking(
    backup_system: tuple,
) -> None:
    store, vault, backups = backup_system
    repository = store.scope("sample")
    repository.put({"id": "a", "note": "synthetic"})
    before = store.revision
    with pytest.raises(DomainError):
        with store.transaction():
            repository.put({"id": "a", "note": "rolled-back"})
            raise DomainError("synthetic failure")
    assert store.revision == before
    store.touched -= IDLE_SECONDS + 1
    assert store.locked
    assert not backups.error
    store.unlock()
    assert len(backups.list()) == 1
