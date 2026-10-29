import pytest

from packages.modules.tasks import Tasks
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_board_status_change_preserves_task_and_time(store: EncryptedStore) -> None:
    tasks = Tasks(store)
    task = tasks.save({"title": "가상 업무", "category": "개발", "priority": "P1"})
    tasks.log(
        {
            "task_id": task["id"],
            "date": "2026-10-30",
            "minutes": 30,
            "status": "in_progress",
        }
    )
    updated = tasks.save({"id": task["id"], "status": "done"})
    assert updated["status"] == "done"
    assert updated["title"] == task["title"]
    assert updated["category"] == "개발"
    assert updated["priority"] == "P1"
    assert tasks.daily("2026-10-30")[0]["minutes"] == 30


def test_tasks_logs_and_input_validation(store: EncryptedStore) -> None:
    tasks = Tasks(store)
    task = tasks.save({"title": "가상 회로 측정", "due": "2026-10-27"})
    tasks.log(
        {"task_id": task["id"], "date": "2026-10-27", "minutes": 130, "status": "done"}
    )
    assert tasks.daily("2026-10-27")[0]["minutes"] == 130
    assert tasks.tasks.get(task["id"])["status"] == "done"
    with pytest.raises(DomainError):
        tasks.save({"title": "가상", "due": "2026-02-30"})
    with pytest.raises(DomainError):
        tasks.log(
            {
                "task_id": task["id"],
                "date": "2026-10-27",
                "minutes": True,
                "status": "done",
            }
        )


def test_daily_task_minutes_limit(store: EncryptedStore) -> None:
    tasks = Tasks(store)
    task = tasks.save({"title": "가상 장시간 업무"})
    data = {
        "task_id": task["id"],
        "date": "2026-10-27",
        "minutes": 1440,
        "status": "in_progress",
    }
    tasks.log(data)
    with pytest.raises(DomainError):
        tasks.log({**data, "minutes": 1})
    assert len(tasks.daily("2026-10-27")) == 1
