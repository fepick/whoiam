import pytest

from packages.modules.attendance import Attendance
from packages.platform.domain import DomainError, moment
from packages.platform.storage import EncryptedStore


@pytest.mark.parametrize(
    ("start", "end", "minutes"),
    [
        ("09:00", "18:00", 480),
        ("12:30", "18:00", 300),
        ("09:00", "12:30", 180),
        ("14:00", "18:00", 240),
        ("09:00", "12:00", 180),
        ("13:00", "18:00", 300),
        ("12:15", "12:45", 0),
    ],
)
def test_break_can_cross_work_boundaries_and_only_overlap_is_deducted(
    store: EncryptedStore, start: str, end: str, minutes: int
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    session = attendance.record(
        {
            "start": f"2026-10-27T{start}:00+09:00",
            "end": f"2026-10-27T{end}:00+09:00",
            "reason": "가상 경계 휴게",
            "breaks": [
                {
                    "start": "2026-10-27T12:00:00+09:00",
                    "end": "2026-10-27T13:00:00+09:00",
                }
            ],
        }
    )
    assert attendance.summary()["today_minutes"] == minutes
    assert (
        session["breaks"][0]["start"] == moment("2026-10-27T12:00:00+09:00").isoformat()
    )


def test_breaks_are_sorted_but_duplicate_break_time_is_not_double_deducted(
    store: EncryptedStore,
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    record = {
        "start": "2026-10-27T09:00:00+09:00",
        "end": "2026-10-27T18:00:00+09:00",
        "reason": "가상 휴게",
        "breaks": [
            {"start": "2026-10-27T12:00:00+09:00", "end": "2026-10-27T13:00:00+09:00"},
            {"start": "2026-10-27T10:00:00+09:00", "end": "2026-10-27T10:15:00+09:00"},
        ],
    }
    session = attendance.record(record)
    assert attendance.summary()["today_minutes"] == 465
    assert (
        session["breaks"][0]["start"] == moment("2026-10-27T10:00:00+09:00").isoformat()
    )
    record["breaks"].append(
        {"start": "2026-10-27T12:30:00+09:00", "end": "2026-10-27T13:30:00+09:00"}
    )
    with pytest.raises(DomainError, match="휴게 시간끼리"):
        attendance.record(record)
    assert attendance.list() == [session]


def test_break_crossing_week_boundary_is_clipped_for_each_week(
    store: EncryptedStore,
) -> None:
    attendance = Attendance(store, lambda: moment("2026-10-27T20:00:00+09:00"))
    attendance.record(
        {
            "start": "2026-10-25T23:30:00+09:00",
            "end": "2026-10-26T01:00:00+09:00",
            "reason": "가상 야간 휴게",
            "breaks": [
                {
                    "start": "2026-10-25T23:00:00+09:00",
                    "end": "2026-10-26T00:15:00+09:00",
                }
            ],
        }
    )
    assert (
        attendance.summary(moment("2026-10-25T12:00:00+09:00").date())["week_minutes"]
        == 0
    )
    assert (
        attendance.summary(moment("2026-10-26T12:00:00+09:00").date())["week_minutes"]
        == 45
    )
