import pytest

from packages.modules.inventory import Inventory
from packages.modules.purchasing import Purchasing
from packages.modules.sensitive import Sensitive
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_partial_receipts_and_pack_conversion(store: EncryptedStore) -> None:
    inventory = Inventory(store)
    item = inventory.save_item({"name": "가상 저항"})
    purchasing = Purchasing(store, inventory, Sensitive(store))
    order = purchasing.create(
        {
            "supplier": "가상 판매처",
            "lines": [
                {
                    "name": "가상 저항 100개 묶음",
                    "item_id": item["id"],
                    "quantity": 3,
                    "units_per_pack": 100,
                }
            ],
        }
    )
    assert inventory.balance(item["id"]) == 0
    receipt = {"id": order["id"], "line_id": order["lines"][0]["id"], "quantity": 1}
    assert purchasing.receive(receipt)["status"] == "partial"
    assert inventory.balance(item["id"]) == 100
    with pytest.raises(DomainError):
        purchasing.receive({**receipt, "quantity": 3})
    assert inventory.balance(item["id"]) == 100
    assert purchasing.receive({**receipt, "quantity": 2})["status"] == "received"
    assert inventory.balance(item["id"]) == 300
    assert len(purchasing.pending()) == 1
