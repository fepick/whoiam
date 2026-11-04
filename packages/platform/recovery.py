"""표준 Scrypt와 Fernet을 사용하는 별도 복구 파일. 암호는 인자로 받지 않는다."""

from __future__ import annotations

import base64
import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from packages.platform.backups import readonly, verify_database
from packages.platform.domain import DomainError, Json
from packages.platform.runtime import PROJECT_ROOT, private_directory, write_new_json
from packages.platform.vault import Vault

#: 복구 암호의 오프라인 추측 비용. 파일 입력으로 KDF 비용을 변경하지 못한다.
SCRYPT_N = 2**17
RECOVERY_SUFFIX = ".whoiam-recovery"


def password_cipher(password: str, salt: bytes) -> Fernet:
    if len(password) < 12 or len(password) > 1024:
        raise DomainError("복구 암호는 12~1024자로 입력해주세요.")
    key = Scrypt(salt=salt, length=32, n=SCRYPT_N, r=8, p=1).derive(
        password.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(key))


def export_recovery(vault: Vault, destination: Path, password: str) -> None:
    destination = destination.expanduser().resolve()
    if (
        destination.suffix != RECOVERY_SUFFIX
        or destination.is_relative_to(PROJECT_ROOT)
        or ".private" in destination.parts
    ):
        raise DomainError(
            "복구 파일은 저장소·.private 밖의 별도 위치에 .whoiam-recovery 확장자로 지정해주세요."
        )
    if not destination.parent.is_dir():
        raise DomainError("복구 파일을 보관할 별도 디렉터리를 먼저 준비해주세요.")
    identity = vault.existing_identity()
    key = vault.keys.load(identity["profile"], identity["vault_id"])
    salt = os.urandom(16)
    token = (
        password_cipher(password, salt)
        .encrypt(json.dumps({**identity, "key": key.decode("ascii")}).encode())
        .decode("ascii")
    )
    try:
        write_new_json(
            destination,
            {
                "format": 1,
                "kdf": "scrypt-17-8-1",
                "salt": base64.b64encode(salt).decode("ascii"),
                "token": token,
            },
        )
    except FileExistsError:
        raise DomainError("기존 복구 파일을 덮어쓰지 않습니다.", 409) from None


def read_recovery(source: Path, password: str) -> tuple[Json, bytes]:
    try:
        if source.is_symlink() or source.stat().st_size > 8192:
            raise ValueError
        envelope = json.loads(source.read_text(encoding="utf-8"))
        if envelope["format"] != 1 or envelope["kdf"] != "scrypt-17-8-1":
            raise ValueError
        salt = base64.b64decode(envelope["salt"], validate=True)
        if len(salt) != 16:
            raise ValueError
        payload = json.loads(password_cipher(password, salt).decrypt(envelope["token"]))
        if payload["format"] != 2 or payload["profile"] not in (
            "production",
            "development",
            "test",
        ):
            raise ValueError
        key = payload.pop("key").encode("ascii")
        Fernet(key)
        return payload, key
    except DomainError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidToken):
        raise DomainError("복구 파일 또는 복구 암호를 확인해주세요.", 409) from None


def recover_backup(vault: Vault, source: Path, identity: Json, key: bytes) -> None:
    if identity["profile"] != vault.paths.profile:
        raise DomainError("다른 실행 프로필로 복구할 수 없습니다.", 409)
    if vault.paths.database.exists() or vault.paths.manifest.exists():
        raise DomainError("복구는 비어 있는 데이터 홈에서만 실행할 수 있습니다.", 409)
    vault.keys.account(identity["profile"], identity["vault_id"])
    verify_database(source, Fernet(key), identity)
    private_directory(vault.paths.root)
    private_directory(vault.paths.database.parent)
    temporary = vault.paths.database.with_name(f"recovery-{uuid4().hex}.sqlite3")
    try:
        incoming = readonly(source)
        target = sqlite3.connect(temporary)
        try:
            incoming.backup(target)
        finally:
            incoming.close()
            target.close()
        verify_database(temporary, Fernet(key), identity)
        vault.initialize(key, identity["vault_id"])
        os.replace(temporary, vault.paths.database)
    finally:
        temporary.unlink(missing_ok=True)
