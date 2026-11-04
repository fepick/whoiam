import base64
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.server.api import create_app
from packages.core import Core
from packages.platform.domain import DomainError
from packages.platform.storage import IDLE_SECONDS, EncryptedStore


def test_concurrent_retries_apply_stock_change_once(store: EncryptedStore) -> None:
    core = Core(store)
    item = core.inventory.save_item({"name": "가상 소자"})
    request_id = str(uuid4())

    def command(index: int) -> dict:
        return core.execute(
            "inventory.move",
            {"item_id": item["id"], "delta": 200, "reason": "가상 입고"},
            request_id,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(command, range(8)))
    assert len({row["id"] for row in results}) == 1
    assert core.inventory.balance(item["id"]) == 200


def test_attachment_link_failure_rolls_back_document(store: EncryptedStore) -> None:
    core = Core(store)
    content = base64.b64encode(b"%PDF-1.4 synthetic-only").decode()
    with pytest.raises(DomainError):
        core.execute(
            "purchasing.document",
            {
                "order_id": "not-found",
                "name": "synthetic.pdf",
                "kind": "statement",
                "content": content,
            },
            str(uuid4()),
        )
    assert core.sensitive.documents.all() == []
    assert core.sensitive.audit.all() == []


def test_polling_does_not_extend_unlock_and_limits_are_enforced(
    store: EncryptedStore,
) -> None:
    with TestClient(
        create_app(store, demo=True), base_url="http://127.0.0.1:4173"
    ) as client:
        client.get("/")
        csrf = client.get("/api/status").json()["csrf"]
        touched = store.touched
        assert client.get("/api/snapshot").status_code == 200
        assert store.touched == touched
        assert (
            client.get(
                "/api/snapshot", headers={"sec-fetch-site": "cross-site"}
            ).status_code
            == 403
        )
        headers = {
            "origin": "http://127.0.0.1:4173",
            "x-whoiam-csrf": csrf,
            "content-length": str(9 * 1024 * 1024),
        }
        assert (
            client.post(
                "/api/commands",
                content=b"{}",
                headers={**headers, "content-type": "application/json"},
            ).status_code
            == 413
        )
        store.touched -= IDLE_SECONDS + 1
        assert client.get("/api/status").json()["locked"]
        assert client.get("/api/snapshot").status_code == 423
