from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.platform.storage import EncryptedStore


def test_autostart_requires_authenticated_unlocked_owner(store: EncryptedStore) -> None:
    class FakeStartup:
        def __init__(self) -> None:
            self.enabled = False

        def status(self) -> dict:
            return {"enabled": self.enabled}

        def set(self, enabled: bool) -> dict:
            self.enabled = enabled
            return self.status()

    startup = FakeStartup()
    with TestClient(
        create_app(store, demo=True, autostart=startup),
        base_url="http://127.0.0.1:4173",
    ) as client:
        assert client.get("/api/autostart").status_code == 401
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        assert (
            client.post(
                "/api/autostart", json={"enabled": True}, headers=headers
            ).status_code
            == 200
        )
        assert startup.enabled
        store.lock()
        assert (
            client.post(
                "/api/autostart", json={"enabled": False}, headers=headers
            ).status_code
            == 423
        )
        assert startup.enabled


def test_shutdown_uses_authenticated_session(store: EncryptedStore) -> None:
    app = create_app(store, demo=True)
    stopped = []
    app.state.shutdown = lambda: stopped.append(True)
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.post("/api/shutdown", json={}).status_code == 401
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        response = client.post(
            "/api/shutdown",
            json={},
            headers={"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf},
        )
        assert response.status_code == 200
        assert stopped == [True]
