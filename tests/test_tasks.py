import pytest

from packages.modules.tasks import Tasks
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_estimate_progress_and_legacy_records(store: EncryptedStore) -> None:
    tasks = Tasks(store)
    task = tasks.save({"title": "가상 업무", "estimated_minutes": 90, "progress": 25})
    moved = tasks.save({"id": task["id"], "status": "in_progress"})
    assert moved["estimated_minutes"] == 90
    assert moved["progress"] == 25
    tasks.log(
        {
            "task_id": task["id"],
            "date": "2026-10-30",
            "minutes": 20,
            "status": "in_progress",
            "estimated_minutes": 120,
            "progress": 40,
        }
    )
    saved = tasks.tasks.get(task["id"])
    assert saved["estimated_minutes"] == 120
    assert saved["progress"] == 40
    del saved["estimated_minutes"]
    del saved["progress"]
    saved["eta"] = "2026-11-01T09:00:00+09:00"
    tasks.tasks.put(saved)
    migrated = tasks.save({"id": task["id"], "status": "done"})
    assert migrated["estimated_minutes"] is None
    assert migrated["progress"] == 0
    assert migrated["eta"] == saved["eta"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("progress", -1),
        ("progress", 101),
        ("progress", 1.5),
        ("progress", True),
        ("estimated_minutes", -1),
        ("estimated_minutes", 525601),
        ("estimated_minutes", 1.5),
    ],
)
def test_invalid_estimate_progress(
    store: EncryptedStore, key: str, value: object
) -> None:
    with pytest.raises(DomainError):
        Tasks(store).save({"title": "가상 업무", key: value})


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
