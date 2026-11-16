from typing import Any
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.platform import updates
from packages.platform.storage import EncryptedStore


@pytest.mark.parametrize(
    ("local", "remote", "newer"),
    [
        ("0.05", "v0.05.0", False),
        ("0.05", "v0.05.1", True),
        ("0.9", "0.10", True),
        ("1.0", "0.99", False),
    ],
)
def test_numeric_versions(local: str, remote: str, newer: bool) -> None:
    assert (updates.version_parts(remote) > updates.version_parts(local)) == newer


def test_check_cache_errors_and_release_filter(monkeypatch: Any) -> None:
    checker = updates.Updates()
    monkeypatch.setattr(updates, "latest_release", lambda: {"tag_name": "v0.06"})
    checker.check()
    assert checker.status()["available"] is True
    assert checker.status()["release_url"].endswith("/v0.06")
    assert checker.status(check=True)["status"] == "ok"
    for release in (
        {"tag_name": "v0.07-rc1"},
        {"tag_name": "v0.07", "draft": True},
        {"tag_name": "v0.07", "prerelease": True},
        {"tag_name": []},
    ):
        monkeypatch.setattr(updates, "latest_release", lambda: release)
        checker.check()
        assert checker.status()["status"] == "error"
        assert checker.status()["latest_version"] == "0.06"

    def missing() -> dict[str, Any]:
        raise HTTPError(updates.RELEASE_API, 404, "missing", None, None)

    monkeypatch.setattr(updates, "latest_release", missing)
    checker.check()
    assert checker.status()["status"] == "no_release"
    assert checker.status()["available"] is False


def test_background_checks_are_coalesced_and_manual_checks_throttled(
    monkeypatch: Any,
) -> None:
    started = []

    class FakeThread:
        def __init__(self, target: Any, daemon: bool) -> None:
            self.target = target

        def start(self) -> None:
            started.append(self.target)

    now = [100.0]
    monkeypatch.setattr(updates.threading, "Thread", FakeThread)
    monkeypatch.setattr(updates.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(updates, "latest_release", lambda: {"tag_name": "v0.05"})
    checker = updates.Updates()
    assert checker.status(check=True)["status"] == "checking"
    checker.status(check=True, force=True)
    assert len(started) == 1
    started[0]()
    checker.status(check=True, force=True)
    assert len(started) == 1
    now[0] += 61
    checker.status(check=True, force=True)
    assert len(started) == 2


def test_update_api_auth_and_demo_no_automatic_network(
    store: EncryptedStore, monkeypatch: Any
) -> None:
    app = create_app(store, demo=True)
    starts = []
    checker = app.state.updates
    monkeypatch.setattr(
        checker,
        "status",
        lambda **options: starts.append(options) or {"status": "unchecked"},
    )
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.post("/api/updates/check", json={}).status_code == 401
        client.post(
            "/api/session",
            json={"token": app.state.bootstrap},
            headers={"origin": "http://127.0.0.1:4173"},
        )
        status = client.get("/api/status").json()
        assert starts == [{"check": False}]
        assert status["version"] == updates.VERSION
        assert client.post("/api/updates/check", json={}).status_code == 403
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": status["csrf"]}
        assert (
            client.post("/api/updates/check", json={}, headers=headers).status_code
            == 200
        )
        assert starts[-1] == {"check": True, "force": True}
