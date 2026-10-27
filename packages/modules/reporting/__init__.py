"""실제 업무 로그를 바탕으로 만드는 수정 가능한 일일 보고 초안."""

from __future__ import annotations

from packages.modules.attendance import Attendance
from packages.modules.tasks import Tasks
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
)
from packages.platform.storage import EncryptedStore

#: 한 장 렌더러가 처리하는 표별 최대 업무 수.
MAX_REPORT_ROWS = 100


class Reporting:
    def __init__(
        self, store: EncryptedStore, tasks: Tasks, attendance: Attendance
    ) -> None:
        self.reports = store.scope("reporting.reports")
        self.tasks = tasks
        self.attendance = attendance

    def generate(self, when: str) -> Json:
        date = day(when)
        grouped: dict[str, Json] = {}
        for entry in self.tasks.daily(when):
            row = grouped.setdefault(
                entry["task_id"],
                {
                    "title": entry["title"],
                    "detail": "",
                    "minutes": 0,
                    "status": "진행 중",
                },
            )
            row["minutes"] += entry["minutes"]
            row["status"] = "완료" if entry["status"] == "done" else "진행 중"
            if entry["note"]:
                row["detail"] = (row["detail"] + "\n" + entry["note"]).strip()
        planned = [
            {
                "title": task["title"],
                "detail": task["detail"],
                "priority": task["priority"],
                "eta": (
                    moment(task["eta"]).astimezone(SEOUL).strftime("%Y-%m-%dT%H:%M")
                    if task["eta"]
                    else ""
                ),
            }
            for task in self.tasks.list()
            if task["status"] not in ("done", "archived")
        ]
        previous = next(
            (report for report in self.list() if report["date"] == when), None
        )
        return self.save(
            {
                "id": previous["id"] if previous else uid(),
                "date": when,
                "daily": list(grouped.values()),
                "planned": planned,
                "note": "업무 로그가 아직 입력되지 않았습니다." if not grouped else "",
            },
            attendance_minutes=self.attendance.summary(date)["today_minutes"],
        )

    def save(self, data: Json, attendance_minutes: int | None = None) -> Json:
        fields(data, {"id", "date", "daily", "planned", "note"})
        when = day(text(data, "date", 10)).isoformat()
        normalized: dict[str, list[Json]] = {}
        for group in ("daily", "planned"):
            rows = data.get(group)
            if not isinstance(rows, list) or len(rows) > MAX_REPORT_ROWS:
                raise DomainError("보고 표는 각각 최대 100개 업무까지 지원합니다.")
            normalized[group] = []
            for row in rows:
                fields(
                    row,
                    (
                        {"title", "detail", "minutes", "status"}
                        if group == "daily"
                        else {"title", "detail", "priority", "eta"}
                    ),
                )
                result = {
                    "title": text(row, "title", 64),
                    "detail": text(row, "detail", 2000, False),
                }
                if group == "daily":
                    result["minutes"] = (
                        None
                        if row.get("minutes") is None
                        else integer(row, "minutes", 0, 1440)
                    )
                    result["status"] = choice(row, "status", ("완료", "진행 중"))
                else:
                    result["priority"] = choice(row, "priority", ("P1", "P2", "P3"))
                    eta = text(row, "eta", 16, False)
                    if eta:
                        moment(eta + ":00+09:00")
                    result["eta"] = eta
                normalized[group].append(result)
        identifier = text(data, "id", 64, False) or uid()
        if attendance_minutes is None:
            attendance_minutes = self.attendance.summary(day(when))["today_minutes"]
        return self.reports.put(
            {
                "id": identifier,
                "date": when,
                **normalized,
                "note": text(data, "note", 240, False),
                "attendance_minutes": attendance_minutes,
                "total_minutes": sum(
                    row["minutes"] or 0 for row in normalized["daily"]
                ),
            }
        )

    def get(self, identifier: str) -> Json:
        return self.reports.get(identifier)

    def list(self) -> list[Json]:
        return sorted(
            self.reports.all(), key=lambda report: report["date"], reverse=True
        )
