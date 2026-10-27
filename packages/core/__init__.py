"""모듈 명령 라우팅과 원자적 출퇴근 흐름."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Callable
from uuid import UUID

from loguru import logger

from packages.modules.attendance import Attendance
from packages.modules.inventory import Inventory
from packages.modules.purchasing import Purchasing
from packages.modules.reporting import Reporting
from packages.modules.sensitive import Sensitive
from packages.modules.tasks import Tasks
from packages.platform.domain import (
    SEOUL,
    DomainError,
    Json,
    fields,
    integer,
    moment,
    text,
    utcnow,
)
from packages.platform.storage import EncryptedStore


class Core:
    def __init__(
        self, store: EncryptedStore, clock: Callable[[], datetime] = utcnow
    ) -> None:
        self.store = store
        self.clock = clock
        self.tasks = Tasks(store)
        self.inventory = Inventory(store)
        self.sensitive = Sensitive(store)
        self.attendance = Attendance(store, clock)
        self.purchasing = Purchasing(store, self.inventory, self.sensitive)
        self.reporting = Reporting(store, self.tasks, self.attendance)
        self.settings_repo = store.scope("core.settings")
        self.commands = store.scope("core.commands")

    def settings(self) -> Json:
        rows = self.settings_repo.all()
        return (
            rows[0]
            if rows
            else {
                "id": "preferences",
                "weekly_limit": 3120,
                "timezone": "Asia/Seoul",
                "notifications": True,
            }
        )

    def save_settings(self, data: Json) -> Json:
        fields(data, {"weekly_limit", "notifications"})
        settings = self.settings()
        if "weekly_limit" in data:
            settings["weekly_limit"] = integer(data, "weekly_limit", 60, 10080)
        if "notifications" in data:
            if type(data["notifications"]) is not bool:
                raise DomainError("알림 설정을 확인해주세요.")
            settings["notifications"] = data["notifications"]
        return self.settings_repo.put(settings)

    def today(self) -> str:
        return self.clock().astimezone(SEOUL).date().isoformat()

    def alerts(self) -> list[Json]:
        alerts = []
        for order in self.purchasing.pending():
            if (
                order["status"] != "received"
                and order["eta"]
                and order["eta"] <= self.today()
            ):
                alerts.append(
                    {
                        "title": "도착 예정·지연 주문을 확인해주세요.",
                        "detail": order["memo"] or order["supplier"],
                        "target": "purchases",
                        "id": order["id"],
                    }
                )
            if not order["statement_ref"] or not order["receipt_ref"]:
                alerts.append(
                    {
                        "title": "구매 증빙을 챙겨주세요.",
                        "detail": order["memo"] or order["supplier"],
                        "target": "purchases",
                        "id": order["id"],
                    }
                )
        for item in self.inventory.list():
            if item["quantity"] < item["minimum"]:
                alerts.append(
                    {
                        "title": "최소 재고보다 적습니다.",
                        "detail": item["name"],
                        "target": "stock",
                        "id": item["id"],
                    }
                )
        summary = self.attendance.summary(limit=self.settings()["weekly_limit"])
        if summary["over_limit"]:
            alerts.append(
                {
                    "title": "주간 근무시간 알림 기준을 넘었습니다.",
                    "detail": "근무와 휴게 기록을 확인해주세요.",
                    "target": "time",
                }
            )
        if summary["missing_checkout"]:
            alerts.append(
                {
                    "title": "이전 퇴근 기록을 확인해주세요.",
                    "detail": "24시간 이상 열린 세션입니다. 합계는 잠정값입니다.",
                    "target": "time",
                }
            )
        for task in self.tasks.today(self.clock().astimezone(SEOUL).date()):
            alerts.append(
                {
                    "title": "미완료 업무를 확인해주세요.",
                    "detail": task["title"],
                    "target": "tasks",
                    "id": task["id"],
                }
            )
        logged = {entry["task_id"] for entry in self.tasks.daily(self.today())}
        for task in self.tasks.list():
            if (
                task["status"] == "done"
                and task["id"] not in logged
                and moment(task["updated_at"]).astimezone(SEOUL).date().isoformat()
                == self.today()
            ):
                alerts.append(
                    {
                        "title": "완료 업무의 소요시간을 확인해주세요.",
                        "detail": task["title"],
                        "target": "tasks",
                        "id": task["id"],
                    }
                )
        return alerts

    def snapshot(self) -> Json:
        with self.store.transaction():
            return {
                "today": self.today(),
                "tasks": self.tasks.list(),
                "today_tasks": self.tasks.today(self.clock().astimezone(SEOUL).date()),
                "logs": self.tasks.daily(self.today()),
                "items": self.inventory.list(),
                "inventory": self.inventory.history(),
                "orders": self.purchasing.list(),
                "attendance": self.attendance.summary(
                    limit=self.settings()["weekly_limit"]
                ),
                "sessions": self.attendance.list(),
                "attendance_history": self.attendance.history(),
                "payroll": self.attendance.payroll_list(),
                "reports": self.reporting.list(),
                "vault": self.sensitive.list(),
                "settings": self.settings(),
                "alerts": self.alerts(),
            }

    def start(self, data: Json) -> Json:
        fields(data, set())
        self.attendance.event("start")
        return {
            "message": "출근을 기록했습니다.",
            "tasks": self.tasks.today(self.clock().astimezone(SEOUL).date()),
            "alerts": self.alerts(),
        }

    def finish(self, data: Json) -> Json:
        fields(data, {"date"})
        report = self.reporting.generate(data.get("date", self.today()))
        return {
            "message": "퇴근과 일일 보고 초안을 기록했습니다.",
            "report": report,
            "alerts": self.alerts(),
            "attendance": self.attendance.summary(
                limit=self.settings()["weekly_limit"]
            ),
        }

    def route(self, name: str, data: Json) -> Json:
        handlers: dict[str, Callable[[Json], Json]] = {
            "tasks.save": self.tasks.save,
            "tasks.log": self.tasks.log,
            "tasks.update_log": self.tasks.update_log,
            "inventory.save": self.inventory.save_item,
            "inventory.move": self.inventory.move,
            "inventory.adjust": self.inventory.adjust,
            "inventory.bom": self.inventory.save_bom,
            "inventory.preview": self.inventory.preview,
            "inventory.assemble": self.inventory.assemble,
            "purchasing.create": self.purchasing.create,
            "purchasing.update": self.purchasing.update,
            "purchasing.receive": self.purchasing.receive,
            "purchasing.document": self.attach_document,
            "attendance.record": self.attendance.record,
            "attendance.payroll": self.attendance.save_payroll,
            "sensitive.save": self.sensitive.save,
            "sensitive.remove": self.sensitive.remove,
            "sensitive.upload": self.sensitive.upload,
            "reporting.save": self.reporting.save,
            "reporting.generate": self.generate,
            "core.start": self.start,
            "core.finish": self.finish,
            "core.settings": self.save_settings,
            "core.command": self.language_command,
        }
        if name in ("attendance.break_start", "attendance.break_end"):
            fields(data, set())
            return self.attendance.event(name.split(".")[1])
        if name not in handlers:
            raise DomainError("지원하지 않는 명령입니다.", 404)
        return handlers[name](data)

    def attach_document(self, data: Json) -> Json:
        fields(data, {"order_id", "name", "kind", "content"})
        kind = text(data, "kind", 32)
        if kind not in ("statement", "card-receipt"):
            raise DomainError("구매 증빙 유형을 확인해주세요.")
        document = self.sensitive.upload(
            {key: data.get(key) for key in ("name", "kind", "content")}
        )
        return self.purchasing.update(
            {
                "id": text(data, "order_id", 64),
                "statement_ref" if kind == "statement" else "receipt_ref": document[
                    "id"
                ],
            }
        )

    def generate(self, data: Json) -> Json:
        fields(data, {"date"})
        return self.reporting.generate(text(data, "date", 10))

    def language_command(self, data: Json) -> Json:
        fields(data, {"text"})
        command = text(data, "text", 100).replace(" ", "")
        if command in ("출근", "퇴근", "휴게시작", "휴게종료"):
            name = {
                "출근": "core.start",
                "퇴근": "core.finish",
                "휴게시작": "attendance.break_start",
                "휴게종료": "attendance.break_end",
            }[command]
            return self.route(name, {})
        navigation = {
            "오늘할일": "tasks",
            "업무": "tasks",
            "재고": "stock",
            "구매": "purchases",
            "배송": "purchases",
            "보고": "report",
            "근무": "time",
        }
        if command not in navigation:
            raise DomainError(
                "출근·퇴근·휴게 시작·휴게 종료·오늘 할 일·재고·배송·보고 중 하나를 입력해주세요."
            )
        return {"navigate": navigation[command]}

    def execute(self, name: str, data: Json, request_id: str) -> Json:
        try:
            UUID(request_id)
        except (ValueError, TypeError, AttributeError):
            raise DomainError("명령의 요청 ID를 확인해주세요.") from None
        fingerprint = hashlib.sha256(
            json.dumps(
                {"name": name, "data": data}, sort_keys=True, ensure_ascii=False
            ).encode()
        ).hexdigest()
        is_finish = name == "core.finish" or (
            name == "core.command"
            and isinstance(data.get("text"), str)
            and data["text"].strip().replace(" ", "") == "퇴근"
        )
        if is_finish:
            fields(data, {"text"} if name == "core.command" else set())
            return self.durable_finish(request_id, fingerprint)
        with self.store.transaction():
            try:
                previous = self.commands.get(request_id)
            except DomainError as error:
                if error.status != 404:
                    raise
                previous = None
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise DomainError(
                        "같은 요청 ID를 다른 명령에 사용할 수 없습니다.", 409
                    )
                return previous["result"]
            result = self.route(name, data)
            self.commands.put(
                {"id": request_id, "fingerprint": fingerprint, "result": result}
            )
            return result

    def durable_finish(self, request_id: str, fingerprint: str) -> Json:
        with self.store.transaction():
            try:
                entry = self.commands.get(request_id)
            except DomainError as error:
                if error.status != 404:
                    raise
                self.attendance.event("finish")
                entry = {
                    "id": request_id,
                    "fingerprint": fingerprint,
                    "phase": "finished",
                    "date": self.today(),
                }
                self.commands.put(entry)
            if entry["fingerprint"] != fingerprint:
                raise DomainError("같은 요청 ID를 다른 명령에 사용할 수 없습니다.", 409)
            if entry.get("phase") != "finished":
                return entry["result"]
        try:
            with self.store.transaction():
                # 다른 재시도가 먼저 보고 생성을 끝낸 경우 그 결과를 사용한다.
                entry = self.commands.get(request_id)
                if entry.get("phase") != "finished":
                    return entry["result"]
                result = self.finish({"date": entry["date"]})
                self.commands.put({**entry, "phase": "completed", "result": result})
                return result
        except Exception:
            logger.error(
                "Report preparation failed after durable checkout; details omitted"
            )
            return {
                "message": "퇴근은 기록했습니다. 보고 생성에 실패했으니 기록 메뉴에서 다시 생성해주세요.",
                "report": None,
                "alerts": [],
            }
