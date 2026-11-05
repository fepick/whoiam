from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.manage import migrate_legacy
from apps.server.api import create_app
from packages.platform.backups import Backups
from packages.platform.runtime import RuntimePaths
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault, VaultKeys
from tests.test_runtime import MemoryKeys


def test_idle_setting_validation_persistence_and_poll_expiry(
    store: EncryptedStore,
) -> None:
    app = create_app(store, demo=True)
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        assert store.idle_seconds == 900
        for value, status in ((0, 400), (241, 400), (True, 400), (1.5, 400), (30, 200)):
            response = client.post(
                "/api/commands",
                json={
                    "name": "core.settings",
                    "data": {"idle_minutes": value},
                    "request_id": str(uuid4()),
                },
                headers=headers,
            )
            assert response.status_code == status
        assert store.idle_seconds == 1800
        store.touched -= 1000
        touched = store.touched
        assert client.get("/api/snapshot").status_code == 200
        assert store.touched == touched
        store.touched -= 801
        assert client.get("/api/status").json()["locked"] is True
        assert client.post("/api/unlock", json={}, headers=headers).status_code == 200
        assert store.idle_seconds == 1800
    reopened = EncryptedStore(store.path, store.key_loader)
    try:
        reopened.unlock()
        create_app(reopened, demo=True)
        assert reopened.idle_seconds == 1800
    finally:
        reopened.close()


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
