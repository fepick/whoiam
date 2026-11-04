from typing import Any
from uuid import uuid4

import pytest

from packages.core import Core
from packages.modules.attendance import Attendance
from packages.platform.domain import DomainError, Json, moment
from packages.platform.storage import EncryptedStore


def manual(start: str, end: str, breaks: list[Json] | None = None) -> Json:
    return {
        "start": f"2026-10-27T{start}:00+09:00",
        "end": f"2026-10-27T{end}:00+09:00",
        "reason": "가상 수동 우선 정정",
        "breaks": breaks or [],
    }


def test_latest_manual_record_replaces_whole_overlapping_record(
    store: EncryptedStore,
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    original = attendance.record(manual("09:00", "18:00"))
    latest = attendance.record(manual("10:00", "17:00"))
    assert len(attendance.list()) == 1
    assert attendance.list()[0]["id"] == latest["id"]
    assert latest["replaces"] == [original["id"]]
    assert attendance.summary()["today_minutes"] == 420
    assert attendance.history()[0]["start"] == original["start"]
    assert attendance.sessions.get(original["id"])["superseded_by"] == latest["id"]


def test_manual_replaces_open_clock_and_uses_manual_breaks(
    store: EncryptedStore,
) -> None:
    now = [moment("2026-10-27T09:00:00+09:00")]
    attendance = Attendance(store, lambda: now[0])
    clock = attendance.event("start")
    now[0] = moment("2026-10-27T12:00:00+09:00")
    attendance.event("break_start")
    now[0] = moment("2026-10-27T13:00:00+09:00")
    attendance.event("break_end")
    now[0] = moment("2026-10-27T20:00:00+09:00")
    latest = attendance.record(
        manual(
            "09:00",
            "18:00",
            [
                {
                    "start": "2026-10-27T13:00:00+09:00",
                    "end": "2026-10-27T13:30:00+09:00",
                }
            ],
        )
    )
    assert latest["source"] == "manual"
    assert attendance.active() is None
    assert attendance.summary()["today_minutes"] == 510
    assert attendance.history()[0]["end"] is None
    assert (
        attendance.sessions.get(clock["id"])["breaks"][0]["end"]
        == moment("2026-10-27T13:00:00+09:00").isoformat()
    )


def test_multiple_overlaps_boundary_and_edit(store: EncryptedStore) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    first = attendance.record(manual("09:00", "12:00"))
    second = attendance.record(manual("13:00", "17:00"))
    outside = attendance.record(manual("18:00", "19:00"))
    merged = attendance.record(manual("10:00", "18:00"))
    assert set(merged["replaces"]) == {first["id"], second["id"]}
    assert {row["id"] for row in attendance.list()} == {merged["id"], outside["id"]}
    assert attendance.summary()["today_minutes"] == 540
    edited = attendance.record({**manual("08:00", "19:00"), "id": merged["id"]})
    assert len(attendance.list()) == 1
    assert edited["corrections"][-1]["previous"]["start"] == merged["start"]
    assert attendance.summary()["today_minutes"] == 660
    assert any(row["kind"] == "corrected" for row in attendance.history())


def test_replacement_rolls_back_all_changes_on_failure(
    store: EncryptedStore, monkeypatch: Any
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    original = attendance.record(manual("09:00", "18:00"))
    original_put = attendance.sessions.put

    def fail_new_record(row: Json) -> Json:
        if row["source"] == "manual" and not row.get("superseded_by"):
            raise DomainError("synthetic storage failure")
        return original_put(row)

    monkeypatch.setattr(attendance.sessions, "put", fail_new_record)
    with pytest.raises(DomainError):
        attendance.record(manual("10:00", "17:00"))
    assert attendance.list() == [original]
    assert attendance.history() == []


def test_retry_does_not_duplicate_replacement(store: EncryptedStore) -> None:
    core = Core(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    core.attendance.record(manual("09:00", "18:00"))
    request_id = str(uuid4())
    result = core.execute("attendance.record", manual("10:00", "17:00"), request_id)
    assert (
        core.execute("attendance.record", manual("10:00", "17:00"), request_id)
        == result
    )
    assert len(core.attendance.list()) == 1
    assert len(core.attendance.history()) == 1
