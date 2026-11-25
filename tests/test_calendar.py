from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.core import Core
from packages.platform.domain import moment
from packages.platform.storage import EncryptedStore


def test_monthly_calendar_splits_work_at_seoul_midnight(store: EncryptedStore) -> None:
    now = [moment("2028-03-01T01:30:00+09:00")]
    core = Core(store, lambda: now[0])
    core.attendance.record(
        {
            "start": "2028-02-29T23:00:00+09:00",
            "end": "2028-03-01T01:00:00+09:00",
            "breaks": [
                {
                    "start": "2028-02-29T23:45:00+09:00",
                    "end": "2028-03-01T00:15:00+09:00",
                }
            ],
            "reason": "가상 자정 근무",
        }
    )
    core.attendance.event("start")
    now[0] = moment("2028-03-01T02:00:00+09:00")
    task = core.tasks.save({"title": "가상 경계 업무"})
    log = core.tasks.log(
        {
            "task_id": task["id"],
            "date": "2028-02-29",
            "status": "done",
            "minutes": 0,
            "note": "가상 완료 메모",
        }
    )
    core.tasks.log(
        {"task_id": task["id"], "date": "2028-03-01", "status": "done", "minutes": 90}
    )

    february = core.monthly_calendar("2028-02")
    assert february["first_weekday"] == 1
    assert len(february["days"]) == 29
    assert february["work_minutes"] == 45
    assert february["days"][-1] == {
        "date": "2028-02-29",
        "work_minutes": 45,
        "provisional": False,
        "logs": [log],
    }
    march = core.monthly_calendar("2028-03")
    assert march["work_minutes"] == 75
    assert march["days"][0]["provisional"] is True
    assert march["days"][0]["logs"][0]["minutes"] == 90
    assert march["days"][1]["provisional"] is False


def test_monthly_calendar_api_keeps_work_records_behind_session_and_lock(
    store: EncryptedStore,
) -> None:
    app = create_app(store, demo=True)
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        assert client.get("/api/calendar?month=2026-11").status_code == 401
        client.get("/")
        assert client.get("/api/calendar?month=2026-13").status_code == 400
        assert client.get("/api/calendar?month=9999-12").status_code == 400
        response = client.get("/api/calendar?month=2026-11")
        assert response.headers["cache-control"] == "no-store"
        assert len(response.json()["days"]) == 30
        assert response.json()["work_minutes"] == 0
        store.lock()
        assert client.get("/api/calendar?month=2026-11").status_code == 423
