from uuid import uuid4

from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.platform.storage import EncryptedStore


def test_local_auth_csrf_lock_and_redacted_validation(store: EncryptedStore) -> None:
    app = create_app(store)
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.get("/api/snapshot").status_code == 401
        assert client.get("/").status_code == 200
        assert client.get("/api/status").status_code == 401
        origin = {"origin": "http://127.0.0.1:4173"}
        assert (
            client.post(
                "/api/session", json={"token": "synthetic-invalid"}, headers=origin
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/session", json={"token": app.state.bootstrap}, headers=origin
            ).status_code
            == 200
        )
        csrf = client.get("/api/status").json()["csrf"]
        body = {
            "name": "tasks.save",
            "data": {"title": "가상 업무"},
            "request_id": str(uuid4()),
        }
        assert client.post("/api/commands", json=body).status_code == 403
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        assert (
            client.post("/api/commands", json=body, headers=headers).status_code == 200
        )
        assert (
            client.post(
                "/api/commands",
                json=body,
                headers={**headers, "origin": "https://example.invalid"},
            ).status_code
            == 403
        )
        invalid = client.post(
            "/api/commands", json=["synthetic-secret"], headers=headers
        )
        assert invalid.status_code == 422 and "synthetic-secret" not in invalid.text
        assert client.get("/.private/database/anything").status_code == 404
        assert (
            client.get("/api/status", headers={"host": "evil.invalid:4173"}).status_code
            == 400
        )
        assert client.post("/api/lock", json={}, headers=headers).status_code == 200
        assert client.get("/api/snapshot").status_code == 423
        assert client.post("/api/unlock", json={}, headers=headers).status_code == 200
        assert len(client.get("/api/snapshot").json()["tasks"]) == 1
