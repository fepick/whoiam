from datetime import datetime

import pytest

from packages.modules.attendance import Attendance
from packages.platform.domain import DomainError, moment
from packages.platform.storage import EncryptedStore


def test_breaks_week_boundary_and_duplicate_start(store: EncryptedStore) -> None:
    now = [moment("2026-10-25T23:00:00+09:00")]
    attendance = Attendance(store, lambda: now[0])
    attendance.event("start")
    with pytest.raises(DomainError):
        attendance.event("start")
    now[0] = moment("2026-10-26T00:30:00+09:00")
    attendance.event("break_start")
    now[0] = moment("2026-10-26T01:00:00+09:00")
    attendance.event("break_end")
    now[0] = moment("2026-10-26T02:00:00+09:00")
    attendance.event("finish")
    assert attendance.summary(datetime(2026, 10, 25).date())["week_minutes"] == 60
    assert attendance.summary(datetime(2026, 10, 26).date())["week_minutes"] == 90
    assert (
        attendance.save_payroll(
            {"month": "2026-10", "expected_net": 3000000, "received_net": 2900000}
        )["difference"]
        == -100000
    )


def test_correction_overlap_and_limit(store: EncryptedStore) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-30T23:00:00+09:00"))
    record = {
        "start": "2026-10-26T09:00:00+09:00",
        "end": "2026-10-26T18:00:00+09:00",
        "reason": "가상 정정",
    }
    attendance.record(record)
    attendance.record(record)
    assert len(attendance.list()) == 1
    assert len(attendance.history()) == 1
    assert attendance.summary(limit=480)["over_limit"]


def test_clock_in_cannot_overlap_recent_corrected_end(store: EncryptedStore) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T09:00:00+09:00"))
    attendance.record(
        {
            "start": "2026-10-27T08:00:00+09:00",
            "end": "2026-10-27T09:02:00+09:00",
            "reason": "가상 시계 오차 정정",
        }
    )
    with pytest.raises(DomainError):
        attendance.event("start")


@pytest.mark.parametrize(
    ("start", "end", "minutes"),
    [
        ("2026-10-27T09:00:00+09:00", "2026-10-27T18:00:00+09:00", 540),
        ("2026-10-27T00:00:00+09:00", "2026-10-27T12:00:00+09:00", 720),
        ("2026-10-26T23:00:00+09:00", "2026-10-27T02:00:00+09:00", 180),
    ],
)
def test_manual_morning_afternoon_noon_and_midnight(
    store: EncryptedStore, start: str, end: str, minutes: int
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    session = attendance.record(
        {"start": start, "end": end, "reason": "가상 시각 검증"}
    )
    assert attendance.seconds(session, moment(start), moment(end)) // 60 == minutes


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        ("2026-10-27T09:00:00+09:00", "2026-10-27T18:00:00+09:00", "미래"),
        ("2026-10-26T18:00:00+09:00", "2026-10-26T09:00:00+09:00", "늦어야"),
        ("2026-10-01T09:00:00+09:00", "2026-10-09T09:00:00+09:00", "7일"),
    ],
)
def test_manual_time_errors_distinguish_future_order_and_duration(
    store: EncryptedStore, start: str, end: str, message: str
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T12:00:00+09:00"))
    with pytest.raises(DomainError, match=message):
        attendance.record({"start": start, "end": end, "reason": "가상 오류 검증"})
    assert attendance.list() == []
