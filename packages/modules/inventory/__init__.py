"""입출고 원장과 불변 BOM 버전의 조립 소모."""

from __future__ import annotations

from packages.platform.domain import (
    DomainError,
    Json,
    fields,
    integer,
    text,
    uid,
    utcnow,
)
from packages.platform.storage import EncryptedStore


class Inventory:
    def __init__(self, store: EncryptedStore) -> None:
        self.store = store
        self.items = store.scope("inventory.items")
        self.movements = store.scope("inventory.movements")
        self.boms = store.scope("inventory.boms")
        self.assemblies = store.scope("inventory.assemblies")

    def get_item(self, identifier: str) -> Json:
        return self.items.get(identifier)

    def history(self) -> Json:
        return {
            "movements": self.movements.all(),
            "assemblies": self.assemblies.all(),
            "boms": self.boms.all(),
        }

    def save_item(self, data: Json) -> Json:
        fields(
            data, {"id", "name", "part_number", "unit", "location", "minimum", "note"}
        )
        old = self.items.get(data["id"]) if data.get("id") else {}
        merged = {"unit": "개", "minimum": 0, **old, **data}
        return self.items.put(
            {
                "id": old.get("id", uid()),
                "name": text(merged, "name", 100),
                "part_number": text(merged, "part_number", 100, False),
                "unit": text(merged, "unit", 16),
                "location": text(merged, "location", 100, False),
                "minimum": integer(merged, "minimum"),
                "note": text(merged, "note", 240, False),
            }
        )

    def balance(self, item_id: str) -> int:
        self.items.get(item_id)
        return sum(
            row["delta"] for row in self.movements.all() if row["item_id"] == item_id
        )

    def list(self) -> list[Json]:
        balances: dict[str, int] = {}
        for row in self.movements.all():
            balances[row["item_id"]] = balances.get(row["item_id"], 0) + row["delta"]
        return [
            {**item, "quantity": balances.get(item["id"], 0)}
            for item in self.items.all()
        ]

    def move(self, data: Json) -> Json:
        fields(data, {"item_id", "delta", "reason", "source"})
        item_id = text(data, "item_id", 64)
        delta = integer(data, "delta", -(10**9), 10**9)
        if delta == 0:
            raise DomainError("변경 수량은 0일 수 없습니다.")
        if self.balance(item_id) + delta < 0:
            raise DomainError("재고가 부족합니다. 차감하지 않았습니다.", 409)
        return self.movements.put(
            {
                "id": uid(),
                "item_id": item_id,
                "delta": delta,
                "reason": text(data, "reason", 240),
                "source": text(data, "source", 64, False),
                "at": utcnow().isoformat(),
            }
        )

    def adjust(self, data: Json) -> Json:
        fields(data, {"item_id", "quantity", "reason"})
        item_id = text(data, "item_id", 64)
        actual = integer(data, "quantity")
        return self.move(
            {
                "item_id": item_id,
                "delta": actual - self.balance(item_id),
                "reason": text(data, "reason", 240),
            }
        )

    def save_bom(self, data: Json) -> Json:
        fields(data, {"name", "version", "lines"})
        name, version = text(data, "name", 100), text(data, "version", 32)
        if any(
            row["name"] == name and row["version"] == version for row in self.boms.all()
        ):
            raise DomainError(
                "이미 존재하는 BOM 버전입니다. 새 버전을 등록해주세요.", 409
            )
        lines = data.get("lines")
        if not isinstance(lines, list) or not 1 <= len(lines) <= 100:
            raise DomainError("BOM에는 1~100개의 소자가 필요합니다.")
        normalized: list[Json] = []
        seen: set[str] = set()
        for line in lines:
            fields(line, {"item_id", "quantity"})
            item = self.items.get(text(line, "item_id", 64))
            if item["id"] in seen:
                raise DomainError("같은 소자는 BOM에 한 번만 등록해주세요.")
            seen.add(item["id"])
            normalized.append(
                {
                    "item_id": item["id"],
                    "name": item["name"],
                    "quantity": integer(line, "quantity", 1, 10**6),
                }
            )
        return self.boms.put(
            {"id": uid(), "name": name, "version": version, "lines": normalized}
        )

    def preview(self, data: Json) -> Json:
        fields(data, {"bom_id", "quantity", "losses", "note"})
        bom = self.boms.get(text(data, "bom_id", 64))
        quantity = integer(data, "quantity", 1, 10**6)
        losses = data.get("losses", {})
        if not isinstance(losses, dict) or set(losses) - {
            line["item_id"] for line in bom["lines"]
        }:
            raise DomainError("추가 손실은 BOM에 포함된 소자만 지정해주세요.")
        lines = []
        for line in bom["lines"]:
            loss = integer({"loss": losses.get(line["item_id"], 0)}, "loss", 0, 10**9)
            required = line["quantity"] * quantity + loss
            available = self.balance(line["item_id"])
            lines.append(
                {
                    **line,
                    "required": required,
                    "loss": loss,
                    "available": available,
                    "shortage": max(0, required - available),
                }
            )
        return {
            "bom": bom,
            "quantity": quantity,
            "lines": lines,
            "can_assemble": all(line["shortage"] == 0 for line in lines),
        }

    def assemble(self, data: Json) -> Json:
        with self.store.transaction():
            preview = self.preview(data)
            if not preview["can_assemble"]:
                raise DomainError(
                    "조립에 필요한 재고가 부족합니다. 전체 작업을 취소했습니다.", 409
                )
            identifier = uid()
            for line in preview["lines"]:
                self.move(
                    {
                        "item_id": line["item_id"],
                        "delta": -line["required"],
                        "reason": "BOM 조립 소모",
                        "source": identifier,
                    }
                )
            return self.assemblies.put(
                {
                    "id": identifier,
                    **preview,
                    "note": text(data, "note", 240, False),
                    "at": utcnow().isoformat(),
                }
            )
