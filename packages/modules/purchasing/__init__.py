"""수동 주문·분할 수령·배송 예정·증빙 참조 관리."""

from __future__ import annotations

from packages.modules.inventory import Inventory
from packages.modules.sensitive import Sensitive
from packages.platform.domain import (
    DomainError,
    Json,
    choice,
    day,
    fields,
    integer,
    text,
    uid,
    utcnow,
)
from packages.platform.storage import EncryptedStore


class Purchasing:
    def __init__(
        self, store: EncryptedStore, inventory: Inventory, sensitive: Sensitive
    ) -> None:
        self.store = store
        self.inventory = inventory
        self.sensitive = sensitive
        self.orders = store.scope("purchasing.orders")
        self.receipts = store.scope("purchasing.receipts")

    def create(self, data: Json) -> Json:
        fields(
            data,
            {"supplier", "order_number", "memo", "project", "eta", "amount", "lines"},
        )
        eta = text(data, "eta", 10, False)
        if eta:
            day(eta)
        lines = data.get("lines")
        if not isinstance(lines, list) or not 1 <= len(lines) <= 100:
            raise DomainError("주문 품목을 1~100개 입력해주세요.")
        normalized = []
        for line in lines:
            fields(line, {"item_id", "name", "quantity", "units_per_pack"})
            item_id = text(line, "item_id", 64, False)
            if item_id:
                self.inventory.get_item(item_id)
            normalized.append(
                {
                    "id": uid(),
                    "item_id": item_id,
                    "name": text(line, "name", 100),
                    "quantity": integer(line, "quantity", 1, 10**6),
                    "units_per_pack": integer(
                        {"units_per_pack": 1, **line}, "units_per_pack", 1, 10**6
                    ),
                    "received": 0,
                    "returned": 0,
                }
            )
        return self.orders.put(
            {
                "id": uid(),
                "supplier": text(data, "supplier", 100),
                "order_number": text(data, "order_number", 100, False),
                "memo": text(data, "memo", 240, False),
                "project": text(data, "project", 100, False),
                "eta": eta,
                "amount": integer({"amount": 0, **data}, "amount", 0, 10**12),
                "lines": normalized,
                "status": "ordered",
                "statement_ref": "",
                "receipt_ref": "",
                "updated_at": utcnow().isoformat(),
            }
        )

    def update(self, data: Json) -> Json:
        fields(data, {"id", "eta", "status", "memo", "statement_ref", "receipt_ref"})
        order = self.orders.get(text(data, "id", 64))
        if "eta" in data:
            eta = text(data, "eta", 10, False)
            if eta:
                day(eta)
            order["eta"] = eta
        if "memo" in data:
            order["memo"] = text(data, "memo", 240, False)
        if "status" in data:
            status = choice(data, "status", ("ordered", "shipping", "cancelled"))
            if any(line["received"] for line in order["lines"]):
                raise DomainError(
                    "수령 이력이 있는 주문은 배송 전 상태로 변경할 수 없습니다."
                )
            order["status"] = status
        for key, kind in (
            ("statement_ref", "statement"),
            ("receipt_ref", "card-receipt"),
        ):
            if key in data:
                reference = text(data, key, 64)
                self.sensitive.validate_document(reference, kind)
                order[key] = reference
        order["updated_at"] = utcnow().isoformat()
        return self.orders.put(order)

    def receive(self, data: Json) -> Json:
        fields(data, {"id", "line_id", "quantity"})
        with self.store.transaction():
            order = self.orders.get(text(data, "id", 64))
            if order["status"] == "cancelled":
                raise DomainError("취소한 주문은 수령할 수 없습니다.")
            line = next(
                (
                    line
                    for line in order["lines"]
                    if line["id"] == text(data, "line_id", 64)
                ),
                None,
            )
            quantity = integer(data, "quantity", 1, 10**6)
            if not line or line["received"] + quantity > line["quantity"]:
                raise DomainError("남은 주문 수량을 초과해 수령할 수 없습니다.", 409)
            receipt_id = uid()
            if line["item_id"]:
                self.inventory.move(
                    {
                        "item_id": line["item_id"],
                        "delta": quantity * line["units_per_pack"],
                        "reason": "구매 수령 입고",
                        "source": receipt_id,
                    }
                )
            line["received"] += quantity
            order["status"] = (
                "received"
                if all(row["received"] == row["quantity"] for row in order["lines"])
                else "partial"
            )
            order["updated_at"] = utcnow().isoformat()
            self.receipts.put(
                {
                    "id": receipt_id,
                    "order_id": order["id"],
                    "line_id": line["id"],
                    "quantity": quantity,
                    "at": utcnow().isoformat(),
                }
            )
            return self.orders.put(order)

    def list(self) -> list[Json]:
        return list(reversed(self.orders.all()))

    def pending(self) -> list[Json]:
        return [
            order
            for order in self.list()
            if order["status"] != "cancelled"
            and (
                order["status"] != "received"
                or not order["statement_ref"]
                or not order["receipt_ref"]
            )
        ]
