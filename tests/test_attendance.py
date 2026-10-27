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
    with pytest.raises(DomainError, match="겹칩니다"):
        attendance.record(record)
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
