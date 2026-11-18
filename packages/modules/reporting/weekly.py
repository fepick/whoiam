"""기간별 업무 로그에 근거한 주간 미팅 발표 초안."""

from packages.modules.tasks import Tasks
from packages.platform.domain import DomainError, Json, fields, text, uid
from packages.platform.storage import EncryptedStore

#: 구분자가 붙은 메모만 해당 발표 항목에 분류한다.
NOTE_SECTIONS = {
    "성과": "주요 성과",
    "주요 성과": "주요 성과",
    "문제": "문제·확인사항",
    "이슈": "문제·확인사항",
    "확인사항": "문제·확인사항",
    "확인 사항": "문제·확인사항",
    "다음 행동": "다음 행동",
    "다음 단계": "다음 행동",
}
#: 업무 로그에 저장되는 상태의 발표용 이름.
STATUS_LABELS = {"done": "완료", "in_progress": "진행 중"}


class WeeklyMeetings:
    def __init__(self, store: EncryptedStore, tasks: Tasks) -> None:
        self.drafts = store.scope("reporting.weekly")
        self.tasks = tasks

    def preview(self, start: str, end: str) -> Json:
        logs = self.tasks.logs_between(start, end)
        return {
            "start_date": start,
            "end_date": end,
            "body": self.outline(start, end, logs) if logs else "",
            "sources": logs,
        }

    @staticmethod
    def outline(start: str, end: str, logs: list[Json]) -> str:
        sections: dict[str, list[str]] = {
            heading: []
            for heading in (
                "주요 성과",
                "완료 업무",
                "진행 중 업무",
                "문제·확인사항",
                "다음 행동",
            )
        }
        grouped: dict[str, list[Json]] = {}
        for log in logs:
            grouped.setdefault(log["task_id"], []).append(log)

        for entries in grouped.values():
            latest = entries[-1]
            title = latest["title"]
            minutes = sum(entry["minutes"] for entry in entries)
            priority = latest.get("priority") or "미기록"
            progress = latest.get("progress")
            progress_label = f"{progress}%" if progress is not None else "미기록"
            work = [
                f"- {title} · {minutes}분 · {latest['date']} 기준 "
                f"우선순위 {priority}, 진행도 {progress_label}"
            ]
            timeline: list[str] = []
            previous_status = None
            seen_notes: set[tuple[str, str]] = set()
            for entry in entries:
                status = entry["status"]
                when = entry["date"]
                if status != previous_status:
                    label = STATUS_LABELS[status]
                    if previous_status == "done" and status == "in_progress":
                        label = "재개"
                    timeline.append(f"{when} {label}")
                    previous_status = status
                for raw_line in entry["note"].splitlines():
                    line = (
                        raw_line.strip().removeprefix("- ").removeprefix("• ").strip()
                    )
                    key = (when, line)
                    if not line or key in seen_notes:
                        continue
                    seen_notes.add(key)
                    prefix, separator, detail = line.replace("：", ":", 1).partition(
                        ":"
                    )
                    section = NOTE_SECTIONS.get(prefix.strip())
                    if section and separator and detail.strip():
                        sections[section].append(
                            f"- {title} · {when} · {detail.strip()}"
                        )
                    else:
                        work.append(f"  - {when} · {line}")
            work.insert(1, "  - 상태 이력 · " + " → ".join(timeline))
            heading = "완료 업무" if latest["status"] == "done" else "진행 중 업무"
            sections[heading].extend(work)

        return "\n\n".join(
            [f"# 주간 미팅 업무 보고\n{start} ~ {end}"]
            + [
                "\n".join([f"## {heading}", *(lines or ["- 기록 없음"])])
                for heading, lines in sections.items()
            ]
        )

    def list(self) -> list[Json]:
        return [
            {key: draft[key] for key in ("id", "start_date", "end_date")}
            for draft in reversed(self.drafts.all())
        ]

    def get(self, identifier: str) -> Json:
        draft = self.drafts.get(identifier)
        ids = {source["id"] for source in draft["sources"]}
        return {
            **draft,
            "sources": [
                log
                for log in self.tasks.logs_between(
                    draft["start_date"], draft["end_date"]
                )
                if log["id"] in ids
            ],
        }

    def save(self, data: Json) -> Json:
        fields(data, {"id", "start_date", "end_date", "body", "source_ids"})
        identifier = text(data, "id", 64, False)
        body = data.get("body")
        if not isinstance(body, str) or not body.strip():
            raise DomainError("발표 초안 내용을 입력해주세요.")
        if identifier:
            if {"start_date", "end_date", "source_ids"} & data.keys():
                raise DomainError(
                    "저장한 초안의 기간과 원본 기록은 변경할 수 없습니다."
                )
            draft = self.drafts.get(identifier)
        else:
            start = text(data, "start_date", 10)
            end = text(data, "end_date", 10)
            source_ids = data.get("source_ids")
            if (
                not isinstance(source_ids, list)
                or not source_ids
                or not all(isinstance(value, str) for value in source_ids)
            ):
                raise DomainError("발표 초안의 원본 업무 로그를 확인해주세요.")
            ids = set(source_ids)
            sources = [
                {"id": log["id"], "date": log["date"]}
                for log in self.tasks.logs_between(start, end)
                if log["id"] in ids
            ]
            if len(sources) != len(ids):
                raise DomainError("기간에 속한 원본 업무 로그만 저장할 수 있습니다.")
            draft = {
                "id": uid(),
                "start_date": start,
                "end_date": end,
                "sources": sources,
            }
        self.drafts.put({**draft, "body": body})
        return {"id": draft["id"]}
