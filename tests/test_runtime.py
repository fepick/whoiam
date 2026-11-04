import shutil
from pathlib import Path

import pytest

from packages.platform.domain import DomainError
from packages.platform.runtime import InstanceLock, RuntimePaths, runtime_paths
from packages.platform.vault import Vault, VaultKeys


class MemoryKeys:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, account: str) -> str | None:
        return self.values.get((service, account))

    def set_password(self, service: str, account: str, value: str) -> None:
        self.values[(service, account)] = value


MemoryKeys.__module__ = "keyring.backends.Windows"


def test_profile_separation_and_stable_vault_identity(tmp_path: Path) -> None:
    provider = VaultKeys(MemoryKeys())
    original = Vault(RuntimePaths("test", tmp_path / "first"), provider)
    key = original.load_key()
    moved_root = tmp_path / "moved"
    shutil.copytree(original.paths.root, moved_root)
    moved = Vault(RuntimePaths("test", moved_root), provider)
    assert moved.load_key() == key
    development = Vault(RuntimePaths("development", tmp_path / "development"), provider)
    assert development.load_key() != key
    with pytest.raises(DomainError):
        runtime_paths("production", str(Path.cwd()))
    with pytest.raises(DomainError):
        runtime_paths("test")


def test_missing_key_or_manifest_never_replaces_existing_data(tmp_path: Path) -> None:
    backend = MemoryKeys()
    vault = Vault(RuntimePaths("test", tmp_path / "synthetic"), VaultKeys(backend))
    vault.load_key()
    backend.values.clear()
    with pytest.raises(DomainError, match="OS 키"):
        vault.load_key()
    assert backend.values == {}
    vault.paths.manifest.unlink()
    vault.paths.database.parent.mkdir()
    vault.paths.database.write_bytes(b"synthetic existing database")
    with pytest.raises(DomainError):
        vault.load_key()
    assert not vault.paths.manifest.exists()


def test_only_one_process_owns_profile(tmp_path: Path) -> None:
    paths = RuntimePaths("test", tmp_path / "synthetic")
    first, second = InstanceLock(paths), InstanceLock(paths)
    first.acquire()
    try:
        with pytest.raises(DomainError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
