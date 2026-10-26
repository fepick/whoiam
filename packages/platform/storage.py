"""인증된 암호문만 저장하는 모듈별 저장소와 원자적 작업 단위."""

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from cryptography.fernet import Fernet, InvalidToken

from packages.platform.domain import DomainError, Json

#: 접근이 없으면 암호화 키 참조를 메모리에서 해제하는 시간.
IDLE_SECONDS = 15 * 60


class EncryptedStore:
    def __init__(self, path: str | Path, key_loader: Callable[[], bytes]) -> None:
        self.path = str(path)
        self.key_loader = key_loader
        self.mutex = threading.RLock()
        self.cipher: Fernet | None = None
        self.connection: sqlite3.Connection | None = None
        self.depth = 0
        self.touched = 0.0

    @property
    def locked(self) -> bool:
        if self.cipher and time.monotonic() - self.touched > IDLE_SECONDS:
            self.lock()
        return self.cipher is None

    def unlock(self) -> None:
        with self.mutex:
            cipher = Fernet(self.key_loader())
            if self.connection is None:
                if self.path != ":memory:":
                    Path(self.path).parent.mkdir(parents=True, exist_ok=True)
                self.connection = sqlite3.connect(self.path, check_same_thread=False)
                self.connection.execute(
                    "CREATE TABLE IF NOT EXISTS records "
                    "(module TEXT, id TEXT, payload BLOB NOT NULL, "
                    "PRIMARY KEY (module, id))"
                )
                self.connection.commit()
            check = self.connection.execute(
                "SELECT payload FROM records WHERE module=? AND id=?",
                ("_format", "key-check"),
            ).fetchone()
            if check:
                try:
                    if cipher.decrypt(check[0]) != b"whoiam-store-v1":
                        raise InvalidToken
                except InvalidToken:
                    raise DomainError(
                        "저장소 키 또는 암호문을 확인해주세요.", 423
                    ) from None
            else:
                self.connection.execute(
                    "INSERT INTO records VALUES (?, ?, ?)",
                    ("_format", "key-check", cipher.encrypt(b"whoiam-store-v1")),
                )
                self.connection.commit()
            self.cipher = cipher
            self.touched = time.monotonic()

    def lock(self) -> None:
        with self.mutex:
            self.cipher = None

    def close(self) -> None:
        with self.mutex:
            self.lock()
            if self.connection:
                self.connection.close()
                self.connection = None

    def require_unlocked(self) -> None:
        if self.locked:
            raise DomainError("보관함을 먼저 잠금 해제해주세요.", 423)
        self.touched = time.monotonic()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self.mutex:
            self.require_unlocked()
            outer = self.depth == 0
            if outer:
                self.connection.execute("BEGIN IMMEDIATE")
            self.depth += 1
            try:
                yield
                if outer:
                    self.connection.commit()
            except BaseException:
                if outer:
                    self.connection.rollback()
                raise
            finally:
                self.depth -= 1

    def scope(self, module: str) -> "Repository":
        return Repository(self, module)


class Repository:
    def __init__(self, store: EncryptedStore, module: str) -> None:
        self.store = store
        self.module = module

    def decode(self, identifier: str, payload: bytes) -> Json:
        try:
            envelope = json.loads(self.store.cipher.decrypt(payload))
            if envelope["module"] != self.module or envelope["id"] != identifier:
                raise InvalidToken
            return envelope["data"]
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise DomainError(
                "암호문 검증에 실패했습니다. 작업을 중단합니다.", 409
            ) from None

    def all(self) -> list[Json]:
        with self.store.mutex:
            self.store.require_unlocked()
            rows = self.store.connection.execute(
                "SELECT id, payload FROM records WHERE module=? ORDER BY rowid",
                (self.module,),
            ).fetchall()
            return [self.decode(identifier, payload) for identifier, payload in rows]

    def get(self, identifier: str) -> Json:
        with self.store.mutex:
            self.store.require_unlocked()
            row = self.store.connection.execute(
                "SELECT payload FROM records WHERE module=? AND id=?",
                (self.module, identifier),
            ).fetchone()
            if not row:
                raise DomainError("항목을 찾을 수 없습니다.", 404)
            return self.decode(identifier, row[0])

    def put(self, data: Json) -> Json:
        with self.store.transaction():
            envelope = {"module": self.module, "id": data["id"], "data": data}
            payload = self.store.cipher.encrypt(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode()
            )
            self.store.connection.execute(
                "INSERT INTO records VALUES (?, ?, ?) "
                "ON CONFLICT(module, id) DO UPDATE SET payload=excluded.payload",
                (self.module, data["id"], payload),
            )
            return data

    def delete(self, identifier: str) -> None:
        with self.store.transaction():
            self.get(identifier)
            self.store.connection.execute(
                "DELETE FROM records WHERE module=? AND id=?", (self.module, identifier)
            )
