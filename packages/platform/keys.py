"""평문·파일 백엔드를 허용하지 않는 OS 키 저장소 연결."""

import hashlib
from pathlib import Path

import keyring
from cryptography.fernet import Fernet

from packages.platform.domain import DomainError

#: 암호화 키 전용 OS 자격증명 서비스 이름.
KEY_SERVICE = "whoiam.local.storage.v1"
#: 확인된 OS 보안 백엔드만 허용한다. 체인과 서드파티 평문 저장은 거부한다.
SECURE_BACKENDS = {
    "keyring.backends.Windows",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
}


def os_key(path: Path) -> bytes:
    """v0.02 저장소 이전 전용. 새 저장소는 vault.VaultKeys를 사용한다."""
    backend = keyring.get_keyring()
    if type(backend).__module__ not in SECURE_BACKENDS:
        raise DomainError("지원하는 OS 보안 키 저장소가 필요합니다.", 503)
    account = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
    try:
        value = backend.get_password(KEY_SERVICE, account)
        if value is None:
            if path.exists():
                raise DomainError(
                    "기존 저장소의 OS 키가 없습니다. 새 키로 덮어쓰지 않습니다.", 423
                )
            value = Fernet.generate_key().decode("ascii")
            backend.set_password(KEY_SERVICE, account, value)
        return value.encode("ascii")
    except DomainError:
        raise
    except Exception:
        raise DomainError("OS 키 저장소에 접근하지 못했습니다.", 503) from None
