"""메모리 전용 가상 데이터. 실제 저장소에는 자동으로 넣지 않는다."""

from datetime import timedelta

from packages.core import Core
from packages.platform.domain import SEOUL, utcnow
from packages.platform.storage import EncryptedStore


def seed(store: EncryptedStore) -> None:
    core = Core(store)
    today = utcnow().astimezone(SEOUL).date()
    for title, priority, category in (
        ("A보드 전원부 측정", "P1", "하드웨어"),
        ("UART 수신 오류 수정", "P2", "임베디드"),
        ("컨트롤 보드 Rev.A 조립", "P2", "하드웨어"),
    ):
        core.tasks.save(
            {
                "title": title,
                "priority": priority,
                "category": category,
                "due": today.isoformat(),
            }
        )
    resistor = core.inventory.save_item(
        {
            "name": "칩 저항 10kΩ",
            "part_number": "DEMO-0603-10K",
            "minimum": 100,
            "location": "부품함 A-02",
        }
    )
    capacitor = core.inventory.save_item(
        {"name": "MLCC 100nF", "minimum": 200, "location": "부품함 B-03"}
    )
    for item, quantity in ((resistor, 500), (capacitor, 150)):
        core.inventory.move(
            {"item_id": item["id"], "delta": quantity, "reason": "가상 초기 재고"}
        )
    core.inventory.save_bom(
        {
            "name": "CTRL-PBA",
            "version": "Rev.A",
            "lines": [
                {"item_id": resistor["id"], "quantity": 12},
                {"item_id": capacitor["id"], "quantity": 8},
            ],
        }
    )
    core.purchasing.create(
        {
            "supplier": "가상 부품몰",
            "memo": "전원부 디커플링 소자 보충",
            "eta": (today + timedelta(days=1)).isoformat(),
            "amount": 12000,
            "lines": [
                {
                    "name": "MLCC 100nF",
                    "item_id": capacitor["id"],
                    "quantity": 3,
                    "units_per_pack": 100,
                }
            ],
        }
    )
