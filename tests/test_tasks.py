import pytest

from packages.modules.tasks import Tasks
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


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
