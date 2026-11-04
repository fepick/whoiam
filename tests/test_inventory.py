import pytest

from packages.modules.inventory import Inventory
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_bom_hundreds_shortage_and_immutable_version(store: EncryptedStore) -> None:
    inventory = Inventory(store)
    resistor = inventory.save_item({"name": "가상 저항"})
    mcu = inventory.save_item({"name": "가상 MCU"})
    inventory.move({"item_id": resistor["id"], "delta": 500, "reason": "가상 입고"})
    inventory.move({"item_id": mcu["id"], "delta": 5, "reason": "가상 입고"})
    data = {
        "name": "가상 PBA",
        "version": "A",
        "lines": [
            {"item_id": resistor["id"], "quantity": 20},
            {"item_id": mcu["id"], "quantity": 1},
        ],
    }
    bom = inventory.save_bom(data)
    with pytest.raises(DomainError):
        inventory.save_bom(data)
    with pytest.raises(DomainError, match="부족"):
        inventory.assemble({"bom_id": bom["id"], "quantity": 10})
    assert inventory.balance(resistor["id"]) == 500
    inventory.move({"item_id": mcu["id"], "delta": 5, "reason": "가상 입고"})
    inventory.assemble(
        {"bom_id": bom["id"], "quantity": 10, "losses": {resistor["id"]: 3}}
    )
    assert inventory.balance(resistor["id"]) == 297
    assert inventory.balance(mcu["id"]) == 0
