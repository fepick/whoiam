from pathlib import Path

from fastapi.testclient import TestClient

from apps.manage import migrate_legacy
from apps.server.api import create_app
from packages.platform.backups import Backups
from packages.platform.runtime import RuntimePaths
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault, VaultKeys
from tests.test_runtime import MemoryKeys


def test_backup_api_auth_and_restore(tmp_path: Path) -> None:
    vault = Vault(RuntimePaths("test", tmp_path / "synthetic"), VaultKeys(MemoryKeys()))
    store = EncryptedStore(vault.paths.database, vault.load_key)
    store.unlock()
    backups = Backups(store, vault)
    store.scope("sample").put({"id": "a", "value": "synthetic-before"})
    app = create_app(store, demo=True, backups=backups)
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.get("/api/backups").status_code == 401
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        snapshot = client.post("/api/backups", json={}, headers=headers).json()
        downloaded = client.get("/api/backups/" + snapshot["id"])
        assert downloaded.status_code == 200
        assert b"synthetic-before" not in downloaded.content
        store.scope("sample").put({"id": "a", "value": "synthetic-after"})
        revision = client.get("/api/backups").json()["revision"]
        assert (
            client.post(
                "/api/backups/restore",
                json={
                    "id": snapshot["id"],
                    "revision": revision,
                    "confirmation": "restore",
                },
                headers=headers,
            ).status_code
            == 200
        )
        assert store.scope("sample").get("a")["value"] == "synthetic-before"
        assert client.post("/api/lock", json={}, headers=headers).status_code == 200
        assert client.get("/api/backups").status_code == 423
    store.close()


def test_explicit_legacy_migration_preserves_source(
    tmp_path: Path, store: EncryptedStore
) -> None:
    store.scope("sample").put({"id": "a", "value": "synthetic-legacy"})
    original = Path(store.path).read_bytes()
    destination = Vault(
        RuntimePaths("test", tmp_path / "new-home"), VaultKeys(MemoryKeys())
    )
    migrate_legacy(Path(store.path), destination, store.key_loader())
    restored = EncryptedStore(destination.paths.database, destination.load_key)
    restored.unlock()
    assert restored.scope("sample").get("a")["value"] == "synthetic-legacy"
    assert Path(store.path).read_bytes() == original
    restored.close()
