from uuid import uuid4

from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.platform.domain import moment
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


def test_manual_attendance_reports_future_end_and_accepts_past_hours(
    store: EncryptedStore,
) -> None:
    app = create_app(store, demo=True)
    app.state.core.attendance.clock = lambda: moment("2026-10-27T12:00:00+09:00")
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        body = {
            "name": "attendance.record",
            "request_id": str(uuid4()),
            "data": {
                "start": "2026-10-27T09:00:00+09:00",
                "end": "2026-10-27T18:00:00+09:00",
                "reason": "가상 수동 기록",
            },
        }
        rejected = client.post("/api/commands", json=body, headers=headers)
        assert rejected.status_code == 400
        assert "미래" in rejected.json()["error"]
        assert app.state.core.attendance.list() == []
        body["data"]["end"] = "2026-10-27T11:00:00+09:00"
        accepted = client.post("/api/commands", json=body, headers=headers)
        assert accepted.status_code == 200
        session = accepted.json()["result"]
        assert session["start"] == "2026-10-27T00:00:00+00:00"
        assert session["end"] == "2026-10-27T02:00:00+00:00"


def test_manual_attendance_api_takes_priority_and_preserves_history(
    store: EncryptedStore,
) -> None:
    app = create_app(store, demo=True)
    app.state.core.attendance.clock = lambda: moment("2026-10-27T20:00:00+09:00")
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        record = {
            "start": "2026-10-27T09:00:00+09:00",
            "end": "2026-10-27T18:00:00+09:00",
            "reason": "가상 기록",
        }
        for start in ("09:00", "10:00"):
            body = {
                "name": "attendance.record",
                "data": {**record, "start": f"2026-10-27T{start}:00+09:00"},
                "request_id": str(uuid4()),
            }
            assert (
                client.post("/api/commands", json=body, headers=headers).status_code
                == 200
            )
        snapshot = client.get("/api/snapshot").json()
        assert len(snapshot["sessions"]) == 1
        assert len(snapshot["attendance_history"]) == 1
        assert snapshot["sessions"][0]["start"] == "2026-10-27T01:00:00+00:00"
