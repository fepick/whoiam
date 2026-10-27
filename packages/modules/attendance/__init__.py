"""출퇴근·명시적 휴게·주간 경계·급여 대조."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

from packages.platform.domain import (
    SEOUL,
    DomainError,
    Json,
    day,
    fields,
    integer,
    moment,
    text,
    uid,
    utcnow,
)
from packages.platform.storage import EncryptedStore

#: 기본 알림 기준이며 법적 근로시간 판정을 대신하지 않는다.
DEFAULT_WEEKLY_MINUTES = 52 * 60


class Attendance:
    def __init__(
        self, store: EncryptedStore, clock: Callable[[], datetime] = utcnow
    ) -> None:
        self.store = store
        self.clock = clock
        self.sessions = store.scope("attendance.sessions")
        self.payroll = store.scope("attendance.payroll")

    def list(self) -> list[Json]:
        return list(reversed(self.sessions.all()))

    def active(self) -> Json | None:
        return next((row for row in self.sessions.all() if row["end"] is None), None)

    def event(self, action: str) -> Json:
        now = self.clock().isoformat()
        active = self.active()
        if action == "start":
            if active:
                raise DomainError("이미 근무 중입니다. 기존 기록을 확인해주세요.", 409)
            if any(
                moment(session["end"]) > moment(now)
                for session in self.sessions.all()
                if session["end"]
            ):
                raise DomainError(
                    "앞선 근무 기록과 겹칩니다. 시스템 시각과 정정 기록을 확인해주세요.",
                    409,
                )
            return self.sessions.put(
                {
                    "id": uid(),
                    "start": now,
                    "end": None,
                    "breaks": [],
                    "corrections": [],
                }
            )
        if active is None:
            raise DomainError("출근 기록이 없습니다.", 409)
        breaks = active["breaks"]
        on_break = bool(breaks and breaks[-1]["end"] is None)
        last = breaks[-1]["end"] or breaks[-1]["start"] if breaks else active["start"]
        if moment(now) < moment(last):
            raise DomainError(
                "시스템 시각이 이전 기록보다 이릅니다. 시간을 확인해주세요.", 409
            )
        if action == "break_start" and not on_break:
            breaks.append({"start": now, "end": None})
        elif action == "break_end" and on_break:
            breaks[-1]["end"] = now
        elif action == "finish":
            if on_break:
                breaks[-1]["end"] = now
            active["end"] = now
        else:
            raise DomainError("현재 상태에서 실행할 수 없는 근무 명령입니다.", 409)
        return self.sessions.put(active)

    def record(self, data: Json) -> Json:
        fields(data, {"id", "start", "end", "breaks", "reason"})
        start, end = moment(text(data, "start", 40)), moment(text(data, "end", 40))
        if end <= start:
            raise DomainError(
                "퇴근 시각은 출근 시각보다 늦어야 합니다. 자정을 넘겼다면 퇴근 날짜를 다음 날로 지정해주세요."
            )
        if end - start > timedelta(days=7):
            raise DomainError(
                "한 번의 근무 기록은 7일을 넘을 수 없습니다. 출근·퇴근 날짜를 확인해주세요."
            )
        if end > self.clock() + timedelta(minutes=5):
            raise DomainError(
                "퇴근 시각이 현재보다 미래입니다(시계 오차 5분 허용). 예정 시각은 저장할 수 없으며, 근무 중에는 출근 기능을 사용해주세요."
            )
        reason = text(data, "reason", 240)
        identifier = text(data, "id", 64, False) or uid()
        breaks = data.get("breaks", [])
        if not isinstance(breaks, list) or len(breaks) > 100:
            raise DomainError("휴게 구간을 확인해주세요.")
        normalized = []
        previous_end = start
        for interval in breaks:
            fields(interval, {"start", "end"})
            break_start, break_end = moment(text(interval, "start", 40)), moment(
                text(interval, "end", 40)
            )
            if (
                not start <= break_start < break_end <= end
                or break_start < previous_end
            ):
                raise DomainError("휴게 구간은 근무 안에서 겹치지 않게 입력해주세요.")
            previous_end = break_end
            normalized.append(
                {"start": break_start.isoformat(), "end": break_end.isoformat()}
            )
        old = None
        for session in self.sessions.all():
            if session["id"] == identifier:
                old = session
                continue
            other_end = moment(session["end"]) if session["end"] else self.clock()
            if start < other_end and end > moment(session["start"]):
                raise DomainError("다른 근무 기록과 시간이 겹칩니다.", 409)
        if data.get("id") and old is None:
            raise DomainError("정정할 근무 기록을 찾을 수 없습니다.", 404)
        corrections = old["corrections"] if old else []
        corrections.append(
            {
                "at": self.clock().isoformat(),
                "reason": reason,
                "previous": (
                    {key: old[key] for key in ("start", "end", "breaks")}
                    if old
                    else None
                ),
            }
        )
        return self.sessions.put(
            {
                "id": identifier,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "breaks": normalized,
                "corrections": corrections,
            }
        )

    def seconds(self, session: Json, start: datetime, end: datetime) -> int:
        left = max(moment(session["start"]), start)
        right = min(moment(session["end"]) if session["end"] else self.clock(), end)
        if right <= left:
            return 0
        seconds = (right - left).total_seconds()
        for interval in session["breaks"]:
            break_left = max(moment(interval["start"]), left)
            break_right = min(
                moment(interval["end"]) if interval["end"] else self.clock(), right
            )
            seconds -= max(0, (break_right - break_left).total_seconds())
        return int(seconds)

    def summary(
        self, when: date | None = None, limit: int = DEFAULT_WEEKLY_MINUTES
    ) -> Json:
        today = when or self.clock().astimezone(SEOUL).date()
        monday = today - timedelta(days=today.weekday())
        beginning = datetime.combine(monday, time.min, SEOUL)
        sessions = self.sessions.all()
        daily = []
        for offset in range(7):
            start = beginning + timedelta(days=offset)
            end = start + timedelta(days=1)
            seconds = sum(self.seconds(session, start, end) for session in sessions)
            daily.append(
                {
                    "date": start.date().isoformat(),
                    "seconds": seconds,
                    "minutes": seconds // 60,
                }
            )
        weekly_minutes = sum(row["seconds"] for row in daily) // 60
        active = self.active()
        return {
            "date": today.isoformat(),
            "week_start": monday.isoformat(),
            "daily": daily,
            "today_minutes": next(
                row["minutes"] for row in daily if row["date"] == today.isoformat()
            ),
            "week_minutes": weekly_minutes,
            "limit_minutes": limit,
            "remaining_minutes": max(0, limit - weekly_minutes),
            "over_limit": weekly_minutes > limit,
            "active": active,
            "provisional": active is not None,
            "missing_checkout": bool(
                active and self.clock() - moment(active["start"]) > timedelta(hours=24)
            ),
        }

    def save_payroll(self, data: Json) -> Json:
        fields(data, {"month", "expected_net", "received_net", "note"})
        month = text(data, "month", 7)
        day(month + "-01")
        expected = integer(data, "expected_net", 0, 10**12)
        received = (
            None
            if data.get("received_net") is None
            else integer(data, "received_net", 0, 10**12)
        )
        return self.payroll.put(
            {
                "id": month,
                "month": month,
                "expected_net": expected,
                "received_net": received,
                "difference": None if received is None else received - expected,
                "note": text(data, "note", 240, False),
            }
        )

    def payroll_list(self) -> list[Json]:
        return sorted(self.payroll.all(), key=lambda row: row["month"], reverse=True)
