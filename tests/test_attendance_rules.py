from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.core import Core
from packages.modules.attendance import Attendance
from packages.modules.attendance.rules import DEFAULT_RULES
from packages.platform.domain import DomainError, moment
from packages.platform.storage import EncryptedStore


@pytest.mark.parametrize(
    ("start", "end", "overtime", "minutes"),
    [
        ("07:00", "17:30", False, 480),
        ("07:00", "17:30", True, 510),
        ("07:00", "20:00", True, 660),
        ("07:00", "07:50", False, 0),
        ("11:30", "12:30", False, 30),
        ("12:15", "12:45", False, 0),
        ("12:30", "13:30", False, 30),
        ("17:10", "17:20", False, 0),
        ("17:10", "17:20", True, 10),
        ("17:20", "17:40", False, 10),
    ],
)
def test_rules_clip_only_overlapping_time(
    store: EncryptedStore, start: str, end: str, overtime: bool, minutes: int
) -> None:
    attendance = Attendance(store, lambda: moment("2026-11-06T23:00:00+09:00"))
    attendance.save_rules({"enabled": True})
    session = attendance.record(
        {
            "start": f"2026-11-06T{start}:00+09:00",
            "end": f"2026-11-06T{end}:00+09:00",
            "reason": "가상 규칙 검증",
            "overtime": overtime,
        }
    )
    summary = attendance.summary()
    assert summary["today_minutes"] == minutes
    assert summary["week_minutes"] == minutes
    assert session["start"] == moment(f"2026-11-06T{start}:00+09:00").isoformat()


def test_overlapping_exclusions_manual_breaks_and_overtime_history(
    store: EncryptedStore,
) -> None:
    attendance = Attendance(store, lambda: moment("2026-11-06T23:00:00+09:00"))
    session = attendance.record(
        {
            "start": "2026-11-06T07:00:00+09:00",
            "end": "2026-11-06T18:00:00+09:00",
            "breaks": [
                {
                    "start": "2026-11-06T11:50:00+09:00",
                    "end": "2026-11-06T13:10:00+09:00",
                },
                {
                    "start": "2026-11-06T17:10:00+09:00",
                    "end": "2026-11-06T17:20:00+09:00",
                },
            ],
            "reason": "가상 중복 구간",
        }
    )
    assert attendance.summary()["today_minutes"] == 570
    attendance.save_rules({"enabled": True})
    assert attendance.summary()["today_minutes"] == 490
    attendance.set_overtime({"id": session["id"], "overtime": True})
    assert attendance.summary()["today_minutes"] == 510
    assert attendance.history()[0]["overtime"] is False
    assert attendance.list()[0]["overtime"] is True
    assert Attendance(store).rules()["enabled"] is True
    attendance.save_rules({"enabled": False})
    assert attendance.summary()["today_minutes"] == 570
    attendance.save_rules(
        {"enabled": True, "lunch_start": "07:30", "lunch_end": "08:30"}
    )
    assert attendance.summary()["today_minutes"] == 480


def test_cross_midnight_week_and_active_clock_record(store: EncryptedStore) -> None:
    now = [moment("2026-11-08T23:00:00+09:00")]
    attendance = Attendance(store, lambda: now[0])
    attendance.save_rules({"enabled": True})
    session = attendance.event("start")
    now[0] = moment("2026-11-09T09:00:00+09:00")
    assert attendance.summary(date(2026, 11, 8))["week_minutes"] == 60
    assert attendance.summary()["today_minutes"] == 60
    attendance.event("finish")
    assert attendance.list()[0]["start"] == session["start"]
    assert attendance.summary()["today_minutes"] == 60


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled": "true"},
        {"earliest_start": "24:00"},
        {"earliest_start": "8:00"},
        {"lunch_start": "13:00", "lunch_end": "12:00"},
        {"preparation_start": "17:00", "preparation_end": "17:00"},
        {"extra": True},
    ],
)
def test_invalid_rules_leave_existing_settings_unchanged(
    store: EncryptedStore, changes: dict[str, object]
) -> None:
    attendance = Attendance(store)
    with pytest.raises(DomainError):
        attendance.save_rules(changes)
    assert attendance.rules() == DEFAULT_RULES


def test_rule_and_overtime_commands_use_normal_api_boundary(
    store: EncryptedStore,
) -> None:
    app = create_app(store, demo=True)
    app.state.core.attendance.clock = lambda: moment("2026-11-06T23:00:00+09:00")
    with TestClient(app, base_url="http://127.0.0.1:4173") as client:
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        headers = {"origin": "http://127.0.0.1:4173", "x-whoiam-csrf": csrf}
        body = {
            "name": "attendance.rules",
            "data": {"enabled": True},
            "request_id": str(uuid4()),
        }
        assert client.post("/api/commands", json=body).status_code == 403
        assert (
            client.post("/api/commands", json=body, headers=headers).status_code == 200
        )
        record = app.state.core.attendance.record(
            {
                "start": "2026-11-06T08:00:00+09:00",
                "end": "2026-11-06T18:00:00+09:00",
                "reason": "가상 API",
            }
        )
        body = {
            "name": "attendance.overtime",
            "data": {"id": record["id"], "overtime": True},
            "request_id": str(uuid4()),
        }
        assert (
            client.post("/api/commands", json=body, headers=headers).status_code == 200
        )
        snapshot = client.get("/api/snapshot").json()
        assert snapshot["attendance_rules"]["enabled"] is True
        assert snapshot["attendance"]["today_minutes"] == 540


def test_reports_use_current_rules_without_rewriting_saved_report_or_task_logs(
    store: EncryptedStore,
) -> None:
    core = Core(store, lambda: moment("2026-11-06T23:00:00+09:00"))
    core.attendance.record(
        {
            "start": "2026-11-06T07:00:00+09:00",
            "end": "2026-11-06T17:30:00+09:00",
            "reason": "가상 보고 검증",
        }
    )
    task = core.tasks.save({"title": "가상 업무"})
    core.tasks.log(
        {"task_id": task["id"], "date": "2026-11-06", "minutes": 30, "status": "done"}
    )
    before = core.generate({"date": "2026-11-06"})
    assert before["attendance_minutes"] == 630
    core.attendance.save_rules({"enabled": True})
    assert core.reporting.list()[0]["attendance_minutes"] == 630
    after = core.generate({"date": "2026-11-06"})
    assert after["attendance_minutes"] == 480
    assert after["daily"][0]["minutes"] == 30
