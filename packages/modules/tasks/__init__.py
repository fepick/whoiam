"""할 일과 날짜별 소요시간 기록."""

from __future__ import annotations

from datetime import date

from packages.platform.domain import (
    SEOUL,
    DomainError,
    Json,
    choice,
    day,
    fields,
    integer,
    moment,
    text,
    uid,
    utcnow,
)
from packages.platform.storage import EncryptedStore

#: 업무의 진행 상태. 기록 삭제 대신 보관 상태를 사용한다.
STATUSES = ("todo", "in_progress", "done", "archived")


class Tasks:
    def __init__(self, store: EncryptedStore) -> None:
        self.tasks = store.scope("tasks")
        self.logs = store.scope("tasks.logs")

    def save(self, data: Json) -> Json:
        fields(
            data,
            {
                "id",
                "title",
                "detail",
                "category",
                "priority",
                "due",
                "eta",
                "status",
                "estimated_minutes",
                "progress",
            },
        )
        old = self.tasks.get(data["id"]) if data.get("id") else {}
        merged = {"priority": "P2", "status": "todo", **old, **data}
        due = text(merged, "due", 10, False)
        eta = text(merged, "eta", 40, False)
        if due:
            day(due)
        if eta:
            moment(eta)
        task = {
            "id": old.get("id", uid()),
            "title": text(merged, "title", 64),
            "detail": text(merged, "detail", 240, False),
            "category": text(merged, "category", 32, False),
            "priority": choice(merged, "priority", ("P1", "P2", "P3")),
            "due": due,
            "eta": eta,
            "estimated_minutes": (
                None
                if merged.get("estimated_minutes") is None
                else integer(merged, "estimated_minutes", 0, 525600)
            ),
            "progress": integer(
                {
                    "progress": old.get(
                        "progress", 100 if old.get("status") == "done" else 0
                    ),
                    **merged,
                },
                "progress",
                0,
                100,
            ),
            "status": choice(merged, "status", STATUSES),
            "updated_at": utcnow().isoformat(),
        }
        return self.tasks.put(task)

    def log(self, data: Json) -> Json:
        fields(
            data,
            {
                "task_id",
                "date",
                "minutes",
                "note",
                "status",
                "progress",
                "estimated_minutes",
            },
        )
        task = self.tasks.get(text(data, "task_id", 64))
        when = day(text(data, "date", 10)).isoformat()
        minutes = integer(data, "minutes", 0, 1440)
        if (
            sum(
                entry["minutes"]
                for entry in self.daily(when)
                if entry["task_id"] == task["id"]
            )
            + minutes
            > 1440
        ):
            raise DomainError(
                "같은 업무의 하루 소요시간 합계는 1440분 이하여야 합니다."
            )
        note = text(data, "note", 240, False)
        status = choice(data, "status", ("in_progress", "done"))
        if "progress" in data:
            task["progress"] = integer(data, "progress", 0, 100)
        if "estimated_minutes" in data:
            task["estimated_minutes"] = (
                None
                if data["estimated_minutes"] is None
                else integer(data, "estimated_minutes", 0, 525600)
            )
        task["status"] = status
        task["updated_at"] = utcnow().isoformat()
        self.tasks.put(task)
        return self.logs.put(
            {
                "id": uid(),
                "task_id": task["id"],
                "title": task["title"],
                "date": when,
                "minutes": minutes,
                "note": note,
                "status": status,
            }
        )

    def list(self) -> list[Json]:
        return sorted(
            self.tasks.all(),
            key=lambda task: (task["priority"], task["due"] or "9999", task["title"]),
        )

    def today(self, when: date | None = None) -> list[Json]:
        today = (when or utcnow().astimezone(SEOUL).date()).isoformat()
        return [
            task
            for task in self.list()
            if task["status"] not in ("done", "archived")
            and (not task["due"] or task["due"] <= today)
        ]

    def daily(self, when: str) -> list[Json]:
        day(when)
        return [entry for entry in self.logs.all() if entry["date"] == when]

    def update_log(self, data: Json) -> Json:
        fields(data, {"id", "minutes", "note"})
        entry = self.logs.get(text(data, "id", 64))
        entry["minutes"] = integer(data, "minutes", 0, 1440)
        if (
            sum(
                row["minutes"]
                for row in self.daily(entry["date"])
                if row["task_id"] == entry["task_id"] and row["id"] != entry["id"]
            )
            + entry["minutes"]
            > 1440
        ):
            raise DomainError(
                "같은 업무의 하루 소요시간 합계는 1440분 이하여야 합니다."
            )
        entry["note"] = text(data, "note", 240, False)
        return self.logs.put(entry)
