import base64

import pytest

from packages.modules.sensitive import Sensitive
from packages.platform.domain import DomainError
from packages.platform.storage import EncryptedStore


def test_credential_reveal_is_scoped_locked_and_audited(store: EncryptedStore) -> None:
    vault = Sensitive(store)
    entry = vault.save(
        {
            "kind": "credential",
            "alias": "가상 로그인",
            "username": "fake@example.invalid",
            "password": "  synthetic-only  ",
        }
    )
    for actor, purpose in (("purchasing", "credential-view"), ("local-ui", "login")):
        with pytest.raises(DomainError) as denied:
            vault.reveal({"id": entry["id"]}, actor, purpose)
        assert denied.value.status == 403
    values = vault.reveal({"id": entry["id"]}, "local-ui", "credential-view")
    assert values == {
        "username": "fake@example.invalid",
        "password": "  synthetic-only  ",
    }
    assert vault.audit.all()[-1]["action"] == "credential.reveal"
    assert all(
        "synthetic-only" not in str(row) and "fake@example.invalid" not in str(row)
        for row in vault.audit.all()
    )
    assert "synthetic-only" not in str(vault.list())
    for kind, extra in (
        ("person", {"name": "가상 사용자"}),
        ("payment-method", {"last_four": "1234"}),
    ):
        other = vault.save({"kind": kind, "alias": "가상 항목", **extra})
        with pytest.raises(DomainError) as denied:
            vault.reveal({"id": other["id"]}, "local-ui", "credential-view")
        assert denied.value.status == 403
    store.lock()
    with pytest.raises(DomainError) as locked:
        vault.reveal({"id": entry["id"]}, "local-ui", "credential-view")
    assert locked.value.status == 423


def test_masked_listing_and_forbidden_raw_access(store: EncryptedStore) -> None:
    vault = Sensitive(store)
    entry = vault.save(
        {
            "kind": "credential",
            "alias": "가상 판매처",
            "username": "fake@example.invalid",
            "password": "synthetic-only-password",
        }
    )
    assert "password" not in str(vault.list())
    with pytest.raises(DomainError) as denied:
        vault.use(entry["id"], "purchasing", "login")
    assert denied.value.status == 403
    with pytest.raises(DomainError):
        vault.save(
            {
                "kind": "payment-method",
                "alias": "가상 카드",
                "last_four": "1234",
                "cvc": "000",
            }
        )
    assert all("password" not in str(row) for row in vault.audit.all())


def test_encrypted_document_and_kind_check(store: EncryptedStore) -> None:
    vault = Sensitive(store)
    document = vault.upload(
        {
            "name": "synthetic.pdf",
            "kind": "statement",
            "content": base64.b64encode(b"%PDF-1.4 synthetic fixture").decode(),
        }
    )
    assert "content" not in document
    vault.validate_document(document["id"], "statement")
    with pytest.raises(DomainError):
        vault.validate_document(document["id"], "card-receipt")
    store.lock()
    with pytest.raises(DomainError):
        vault.document(document["id"])
