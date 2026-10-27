"""일반 조회에 원문을 반환하지 않는 로컬 민감정보 경계."""

from __future__ import annotations

import base64
import binascii

from packages.platform.domain import (
    DomainError,
    Json,
    choice,
    fields,
    text,
    uid,
    utcnow,
)
from packages.platform.storage import EncryptedStore

#: 증빙 파일 하나의 최대 원문 크기.
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
#: 원문 사용은 승인된 로컬 연동 목적에 한정한다. 현재 외부 연동은 없다.
ALLOWED_PURPOSES: dict[str, set[str]] = {}


class Sensitive:
    def __init__(self, store: EncryptedStore) -> None:
        self.store = store
        self.entries = store.scope("sensitive.entries")
        self.documents = store.scope("sensitive.documents")
        self.audit = store.scope("sensitive.audit")

    def record_audit(self, action: str, reference: str) -> None:
        self.audit.put(
            {
                "id": uid(),
                "action": action,
                "reference": reference,
                "at": utcnow().isoformat(),
            }
        )

    def save(self, data: Json) -> Json:
        kind = choice(data, "kind", ("credential", "payment-method", "person"))
        allowed = {
            "credential": {"username", "password"},
            "payment-method": {"issuer", "last_four", "token"},
            "person": {"name", "email", "phone", "address"},
        }[kind]
        fields(data, {"id", "kind", "alias"} | allowed)
        identifier = text(data, "id", 64, False) or uid()
        if data.get("id"):
            previous = self.entries.get(identifier)
            if previous["kind"] != kind:
                raise DomainError("저장된 정보의 유형을 변경할 수 없습니다.")
        values = {key: text(data, key, 2000, key == "password") for key in allowed}
        if kind == "credential":
            values["password"] = data["password"]
        if kind == "payment-method" and (
            len(values["last_four"]) != 4
            or not values["last_four"].isascii()
            or not values["last_four"].isdigit()
        ):
            raise DomainError("카드 끝 네 자리만 입력해주세요.")
        entry = {
            "id": identifier,
            "kind": kind,
            "alias": text(data, "alias", 64),
            "values": values,
        }
        self.entries.put(entry)
        self.record_audit("entry.save", identifier)
        return self.mask(entry)

    def mask(self, entry: Json) -> Json:
        hint = "••••"
        if entry["kind"] == "payment-method":
            hint = "•••• " + entry["values"]["last_four"]
        return {
            "id": entry["id"],
            "kind": entry["kind"],
            "alias": entry["alias"],
            "hint": hint,
        }

    def list(self) -> list[Json]:
        return [self.mask(entry) for entry in self.entries.all()]

    def remove(self, data: Json) -> Json:
        fields(data, {"id"})
        identifier = text(data, "id", 64)
        self.entries.delete(identifier)
        self.record_audit("entry.delete", identifier)
        return {"deleted": True}

    def use(self, reference: str, actor: str, purpose: str) -> Json:
        if purpose not in ALLOWED_PURPOSES.get(actor, set()):
            raise DomainError("이 목적의 원문 접근 권한이 없습니다.", 403)
        self.record_audit("entry.use", reference)
        return self.entries.get(reference)["values"]

    def upload(self, data: Json) -> Json:
        fields(data, {"name", "content", "kind"})
        kind = choice(data, "kind", ("statement", "card-receipt", "payroll"))
        content = text(data, "content", (MAX_DOCUMENT_BYTES * 4 // 3) + 8)
        try:
            raw = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            raise DomainError("증빙 파일 형식을 확인해주세요.") from None
        if not 0 < len(raw) <= MAX_DOCUMENT_BYTES:
            raise DomainError("증빙은 5MB 이하만 저장할 수 있습니다.")
        if raw.startswith(b"%PDF-"):
            media_type = "application/pdf"
        elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
            media_type = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            media_type = "image/jpeg"
        else:
            raise DomainError("PDF·PNG·JPEG 파일만 저장할 수 있습니다.")
        document = {
            "id": uid(),
            "name": text(data, "name", 140),
            "kind": kind,
            "content": content,
            "media_type": media_type,
            "size": len(raw),
        }
        self.documents.put(document)
        self.record_audit("document.save", document["id"])
        return {key: value for key, value in document.items() if key != "content"}

    def validate_document(self, reference: str, kind: str) -> None:
        if self.documents.get(reference)["kind"] != kind:
            raise DomainError("증빙 유형이 일치하지 않습니다.")

    def document(self, reference: str) -> Json:
        document = self.documents.get(reference)
        self.record_audit("document.download", reference)
        return document
