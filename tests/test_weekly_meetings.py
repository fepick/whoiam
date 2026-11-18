from uuid import uuid4

from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.core import Core
from packages.platform.storage import EncryptedStore


def test_preview_uses_ordered_historical_logs_across_years(
    store: EncryptedStore,
) -> None:
    core = Core(store)
    task = core.tasks.save({"title": "가상 검증", "priority": "P1"})
    log_data = {"task_id": task["id"], "minutes": 20, "status": "in_progress"}
    long_note = "가" * 200
    reopened = core.tasks.log(
        {
            **log_data,
            "date": "2027-01-01",
            "note": f"문제: 경계 조건 확인\n다음 행동: 재측정\n-20V 측정\n{long_note}",
        }
    )
    core.tasks.logs.put(
        {
            key: value
            for key, value in reopened.items()
            if key not in ("priority", "progress")
        }
    )
    completed = core.tasks.log(
        {
            **log_data,
            "date": "2026-12-31",
            "status": "done",
            "progress": 100,
            "note": "성과: 가상 측정 완료",
        }
    )
    repeated = core.tasks.log(
        {**log_data, "date": "2026-12-31", "status": "done", "note": completed["note"]}
    )
    for outside_date in ("2026-12-30", "2027-01-02"):
        core.tasks.log({**log_data, "date": outside_date, "note": "기간 밖 메모"})
    core.tasks.save({"id": task["id"], "status": "done", "progress": 100})

    draft = core.reporting.weekly.preview("2026-12-31", "2027-01-01")
    assert [row["id"] for row in draft["sources"]] == [
        completed["id"],
        repeated["id"],
        reopened["id"],
    ]
    body = draft["body"]
    assert "## 완료 업무\n- 기록 없음\n\n## 진행 중 업무\n- 가상 검증 · 60분" in body
    assert "2026-12-31 완료 → 2027-01-01 재개" in body
    assert "우선순위 미기록, 진행도 미기록" in body
    assert body.count("가상 측정 완료") == 1
    assert "## 문제·확인사항\n- 가상 검증 · 2027-01-01 · 경계 조건 확인" in body
    assert "## 다음 행동\n- 가상 검증 · 2027-01-01 · 재측정" in body
    assert "-20V 측정" in body and long_note in body and "기간 밖 메모" not in body
    assert core.reporting.weekly.list() == []


def test_weekly_preview_and_edit_save_require_local_access(
    store: EncryptedStore,
) -> None:
    app = create_app(store)
    core = app.state.core
    task = core.tasks.save({"title": "가상 업무"})
    log = core.tasks.log(
        {
            "task_id": task["id"],
            "date": "2026-11-18",
            "minutes": 15,
            "status": "done",
            "note": "원본 메모",
        }
    )
    period = {"start_date": "2026-11-18", "end_date": "2026-11-18"}
    preview = "/api/weekly-meetings/preview"
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.get(preview, params=period).status_code == 401
        origin = {"origin": "http://127.0.0.1:4173"}
        client.post("/api/session", headers=origin, json={"token": app.state.bootstrap})
        headers = {**origin, "x-whoiam-csrf": client.get("/api/status").json()["csrf"]}
        assert (
            client.get(
                preview, params={**period, "start_date": "2026-11-19"}
            ).status_code
            == 400
        )
        assert (
            client.get(preview, params={**period, "end_date": "2026-02-30"}).status_code
            == 400
        )
        empty = client.get(
            preview, params={"start_date": "2026-11-17", "end_date": "2026-11-17"}
        ).json()
        assert empty["body"] == "" and empty["sources"] == []
        response = client.get(preview, params=period)
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["sources"] == [log]
        assert client.get("/api/snapshot").json()["weekly_meetings"] == []

        body = {
            "name": "reporting.weekly_save",
            "request_id": str(uuid4()),
            "data": {**period, "body": "가상 발표 초안", "source_ids": [log["id"]]},
        }
        assert client.post("/api/commands", json=body).status_code == 403
        invalid = {
            **body,
            "data": {
                **body["data"],
                "start_date": "2026-11-17",
                "end_date": "2026-11-17",
            },
        }
        assert (
            client.post("/api/commands", headers=headers, json=invalid).status_code
            == 400
        )
        saved = client.post("/api/commands", headers=headers, json=body).json()[
            "result"
        ]
        assert (
            client.post("/api/commands", headers=headers, json=body).json()["result"]
            == saved
        )
        assert client.get("/api/snapshot").json()["weekly_meetings"] == [
            {**period, **saved}
        ]

        uri = f"/api/weekly-meetings/{saved['id']}"
        edited = "편집한 가상 발표 초안\n" + "나" * 3000
        update = {**body, "request_id": str(uuid4()), "data": {**saved, "body": edited}}
        assert (
            client.post("/api/commands", headers=headers, json=update).status_code
            == 200
        )
        assert client.get(uri).json() == {
            **period,
            **saved,
            "body": edited,
            "sources": [log],
        }
        assert core.tasks.daily(period["start_date"]) == [log]
        assert edited.encode() not in store.connection.serialize()
        client.post("/api/lock", headers=headers, json={})
        assert client.get(preview, params=period).status_code == 423
        assert client.get(uri).status_code == 423
