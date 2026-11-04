from pathlib import Path
from typing import Any

import pytest
from cryptography.fernet import Fernet

from packages.platform import recovery as recovery_module
from packages.platform.backups import Backups
from packages.platform.domain import DomainError
from packages.platform.recovery import export_recovery, read_recovery, recover_backup
from packages.platform.runtime import RuntimePaths
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault, VaultKeys
from tests.test_runtime import MemoryKeys


def test_password_recovery_to_empty_separate_home(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(recovery_module, "PROJECT_ROOT", tmp_path / "synthetic-source")
    vault = Vault(RuntimePaths("test", tmp_path / "old"), VaultKeys(MemoryKeys()))
    store = EncryptedStore(vault.paths.database, vault.load_key)
    store.unlock()
    store.scope("sample").put({"id": "a", "note": "synthetic-recovered"})
    backups = Backups(store, vault)
    snapshot = backups.create()
    recovery = tmp_path / "separate-recovery.whoiam-recovery"
    password = "synthetic-only-recovery-password"
    export_recovery(vault, recovery, password)
    assert b"synthetic-recovered" not in recovery.read_bytes()
    assert vault.load_key() not in recovery.read_bytes()
    with pytest.raises(DomainError):
        read_recovery(recovery, "synthetic-wrong-password")
    identity, key = read_recovery(recovery, password)
    restored_vault = Vault(
        RuntimePaths("test", tmp_path / "new"), VaultKeys(MemoryKeys())
    )
    recover_backup(restored_vault, backups.path(snapshot["id"]), identity, key)
    restored = EncryptedStore(restored_vault.paths.database, restored_vault.load_key)
    restored.unlock()
    assert restored.scope("sample").get("a")["note"] == "synthetic-recovered"
    with pytest.raises(DomainError):
        recover_backup(restored_vault, backups.path(snapshot["id"]), identity, key)
    restored.close()
    store.close()


def test_recovery_file_cannot_be_exported_inside_checkout(tmp_path: Path) -> None:
    vault = Vault(RuntimePaths("test", tmp_path / "synthetic"), VaultKeys(MemoryKeys()))
    with pytest.raises(DomainError):
        export_recovery(
            vault,
            recovery_module.PROJECT_ROOT / "fake.whoiam-recovery",
            "synthetic-test-password",
        )
