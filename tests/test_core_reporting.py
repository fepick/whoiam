from uuid import uuid4

import pytest

from packages.core import Core
from packages.platform.domain import DomainError, moment
from packages.platform.storage import EncryptedStore


def test_start_finish_report_and_idempotency(store: EncryptedStore) -> None:
    now = [moment("2026-10-27T09:00:00+09:00")]
    core = Core(store, lambda: now[0])
    task = core.execute(
        "tasks.save",
        {"title": "가상 업무", "due": "2026-10-27", "priority": "P1"},
        str(uuid4()),
    )
    request_id = str(uuid4())
    first = core.execute("core.command", {"text": "출근"}, request_id)
    assert core.execute("core.command", {"text": "출근"}, request_id) == first
    assert len(core.attendance.list()) == 1
    with pytest.raises(DomainError):
        core.execute("core.command", {"text": "퇴근"}, request_id)
    core.execute(
        "tasks.log",
        {
            "task_id": task["id"],
            "date": "2026-10-27",
            "minutes": 130,
            "status": "done",
            "note": "가상 측정 완료",
        },
        str(uuid4()),
    )
    now[0] = moment("2026-10-27T18:00:00+09:00")
    finished = core.execute("core.finish", {}, str(uuid4()))
    assert finished["report"]["daily"][0]["minutes"] == 130
    assert finished["report"]["attendance_minutes"] == 540
    assert finished["report"]["planned"] == []
    assert core.snapshot()["attendance"]["active"] is None


def test_failed_command_has_no_partial_task_update(store: EncryptedStore) -> None:
    core = Core(store)
    task = core.tasks.save({"title": "가상 업무"})
    with pytest.raises(DomainError):
        core.execute(
            "tasks.log",
            {
                "task_id": task["id"],
                "date": "2026-10-27",
                "minutes": 30,
                "status": "done",
                "note": "x" * 241,
            },
            str(uuid4()),
        )
    assert core.tasks.tasks.get(task["id"])["status"] == "todo"


def test_large_report_preserves_source_and_does_not_block_checkout(
    store: EncryptedStore,
) -> None:
    core = Core(store)
    task = core.tasks.save({"title": "가상 장시간 검증"})
    for _ in range(10):
        core.tasks.log(
            {
                "task_id": task["id"],
                "date": core.today(),
                "minutes": 1,
                "note": "가" * 240,
                "status": "in_progress",
            }
        )
    for index in range(101):
        core.tasks.save({"title": f"가상 예정 {index}"})
    core.execute("core.start", {}, str(uuid4()))
    report = core.execute("core.finish", {}, str(uuid4()))["report"]
    assert len(report["planned"]) == 100
    assert "102" in report["note"]
    assert len(report["daily"][0]["detail"]) <= 2000
    assert sum(len(entry["note"]) for entry in core.tasks.daily(core.today())) == 2400
    assert core.attendance.active() is None
