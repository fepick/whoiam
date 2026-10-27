"""경로와 독립적인 저장소 UUID 및 OS 키의 연결."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.fernet import Fernet

from packages.platform.domain import DomainError, Json
from packages.platform.keys import SECURE_BACKENDS
from packages.platform.runtime import RuntimePaths, private_directory, write_new_json

#: v1의 경로 해시 기반 키와 구분하며 프로필도 키 이름에 포함한다.
VAULT_KEY_SERVICE = "whoiam.local.vault.v2"


class VaultKeys:
    def __init__(self, backend: object | None = None) -> None:
        self.backend = backend

    def provider(self) -> object:
        if self.backend is None:
            import keyring

            self.backend = keyring.get_keyring()
        if type(self.backend).__module__ not in SECURE_BACKENDS:
            raise DomainError("지원하는 OS 보안 키 저장소가 필요합니다.", 503)
        return self.backend

    def account(self, profile: str, identifier: str) -> str:
        try:
            normalized = str(UUID(identifier))
        except (ValueError, TypeError, AttributeError):
            raise DomainError("저장소 식별자가 올바르지 않습니다.") from None
        if profile not in ("production", "development", "test"):
            raise DomainError("실행 프로필을 확인해주세요.")
        return f"{profile}:{normalized}"

    def load(self, profile: str, identifier: str) -> bytes:
        account = self.account(profile, identifier)
        try:
            value = self.provider().get_password(VAULT_KEY_SERVICE, account)
            if value is None:
                raise DomainError("OS 키가 없습니다. 복구 절차를 사용해주세요.", 423)
            key = value.encode("ascii")
            Fernet(key)
            return key
        except DomainError:
            raise
        except Exception:
            raise DomainError("OS 키 저장소에 접근하지 못했습니다.", 503) from None

    def install(self, profile: str, identifier: str, key: bytes) -> None:
        account = self.account(profile, identifier)
        Fernet(key)
        try:
            backend = self.provider()
            previous = backend.get_password(VAULT_KEY_SERVICE, account)
            if previous is not None:
                if not secrets.compare_digest(previous.encode("ascii"), key):
                    raise DomainError("다른 OS 키를 덮어쓰지 않습니다.", 409)
                return
            backend.set_password(VAULT_KEY_SERVICE, account, key.decode("ascii"))
            if backend.get_password(VAULT_KEY_SERVICE, account) != key.decode("ascii"):
                raise DomainError("OS 키 저장을 확인하지 못했습니다.", 503)
        except DomainError:
            raise
        except Exception:
            raise DomainError("OS 키 저장에 실패했습니다.", 503) from None


class Vault:
    def __init__(self, paths: RuntimePaths, keys: VaultKeys | None = None) -> None:
        self.paths = paths
        self.keys = keys or VaultKeys()
        self.identity: Json | None = None

    def existing_identity(self) -> Json:
        try:
            if (
                self.paths.manifest.is_symlink()
                or self.paths.manifest.stat().st_size > 4096
            ):
                raise ValueError
            identity = json.loads(self.paths.manifest.read_text(encoding="utf-8"))
            if (
                not isinstance(identity, dict)
                or identity.get("format") != 2
                or identity.get("profile") != self.paths.profile
            ):
                raise ValueError
            self.keys.account(identity["profile"], identity["vault_id"])
            self.identity = identity
            return identity
        except (OSError, ValueError, KeyError, TypeError):
            raise DomainError(
                "저장소 식별 파일을 확인해주세요. 자동으로 덮어쓰지 않습니다.", 409
            ) from None

    def initialize(
        self, key: bytes | None = None, identifier: str | None = None
    ) -> bytes:
        if self.paths.manifest.exists() or self.paths.database.exists():
            raise DomainError("이미 존재하는 저장소는 초기화하지 않습니다.", 409)
        private_directory(self.paths.root)
        identity = {
            "format": 2,
            "profile": self.paths.profile,
            "vault_id": identifier or str(uuid4()),
        }
        value = key or Fernet.generate_key()
        self.keys.install(identity["profile"], identity["vault_id"], value)
        write_new_json(self.paths.manifest, identity)
        self.identity = identity
        return value

    def load_key(self) -> bytes:
        if self.paths.database.is_symlink() or self.paths.database.parent.is_symlink():
            raise DomainError("저장소 파일에 심볼릭 링크를 사용할 수 없습니다.")
        if self.paths.manifest.exists():
            identity = self.existing_identity()
            return self.keys.load(identity["profile"], identity["vault_id"])
        if self.paths.database.exists():
            raise DomainError(
                "기존 DB에 저장소 식별 파일이 없습니다. 이전·복구 절차가 필요합니다.",
                423,
            )
        return self.initialize()
