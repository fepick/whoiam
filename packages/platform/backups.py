"""암호문 스냅샷 검증·자동 백업·복원 전 백업을 포함한 복원."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import threading
import time
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from packages.platform.domain import DomainError, Json, utcnow
from packages.platform.runtime import private_directory
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault

#: 자동 백업 최대 대기 시간과 최근 복원 지점 보관 개수.
BACKUP_INTERVAL = 5 * 60
BACKUP_KEEP = 30
BACKUP_NAME = re.compile(r"whoiam-\d{8}T\d{12}Z-[a-f0-9]{32}\.sqlite3")


def readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file() or path.is_symlink():
        raise DomainError("백업 파일을 확인해주세요.")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def verify_database(path: Path, cipher: Fernet, identity: Json | None = None) -> Json:
    connection = readonly(path)
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError
        rows = connection.execute("SELECT module, id, payload FROM records").fetchall()
        valid_key = False
        for module, identifier, payload in rows:
            plain = cipher.decrypt(payload)
            if module == "_format" and identifier == "key-check":
                valid_key = plain == b"whoiam-store-v1"
            else:
                envelope = json.loads(plain)
                if (
                    envelope["module"] != module
                    or envelope["id"] != identifier
                    or not isinstance(envelope["data"], dict)
                ):
                    raise ValueError
        if not valid_key:
            raise ValueError
        metadata = {}
        if identity is not None:
            metadata = json.loads(
                connection.execute("SELECT payload FROM backup_info").fetchone()[0]
            )
            if (
                metadata["vault_id"] != identity["vault_id"]
                or metadata["profile"] != identity["profile"]
            ):
                raise DomainError(
                    "다른 저장소·프로필의 백업은 복원할 수 없습니다.", 409
                )
        return metadata
    except DomainError:
        raise
    except (sqlite3.Error, InvalidToken, ValueError, KeyError, TypeError, IndexError):
        raise DomainError("백업의 암호문·구조 검증에 실패했습니다.", 409) from None
    finally:
        connection.close()


class Backups:
    def __init__(self, store: EncryptedStore, vault: Vault) -> None:
        self.store, self.vault = store, vault
        self.last_revision = -1
        self.last_time = 0.0
        self.last_created = ""
        self.error = False
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        store.before_lock = self.before_lock

    def identity(self) -> Json:
        return self.vault.identity or self.vault.existing_identity()

    def path(self, identifier: str) -> Path:
        if not BACKUP_NAME.fullmatch(identifier):
            raise DomainError("백업 식별자를 확인해주세요.")
        path = self.vault.paths.backups / identifier
        if path.is_symlink() or path.parent.is_symlink():
            raise DomainError("백업 경로에 링크를 사용할 수 없습니다.")
        return path

    def list(self) -> list[Json]:
        with self.store.mutex:
            self.store.require_unlocked()
            identity = self.identity()
            rows = []
            if not self.vault.paths.backups.exists():
                return rows
            if self.vault.paths.backups.is_symlink():
                raise DomainError("백업 디렉터리에 링크를 사용할 수 없습니다.")
            for path in sorted(
                self.vault.paths.backups.glob("whoiam-*.sqlite3"), reverse=True
            ):
                if not BACKUP_NAME.fullmatch(path.name) or path.is_symlink():
                    continue
                try:
                    connection = readonly(path)
                    try:
                        metadata = json.loads(
                            connection.execute(
                                "SELECT payload FROM backup_info"
                            ).fetchone()[0]
                        )
                    finally:
                        connection.close()
                    if (
                        metadata["vault_id"] != identity["vault_id"]
                        or metadata["profile"] != identity["profile"]
                    ):
                        continue
                    rows.append(
                        {
                            "id": path.name,
                            "created_at": metadata["created_at"],
                            "reason": metadata["reason"],
                            "size": path.stat().st_size,
                        }
                    )
                except (
                    DomainError,
                    OSError,
                    sqlite3.Error,
                    ValueError,
                    KeyError,
                    TypeError,
                ):
                    continue
            return rows

    def create(self, reason: str = "manual") -> Json:
        with self.store.mutex:
            self.store.require_unlocked()
            identity = self.identity()
            private_directory(self.vault.paths.backups)
            name = (
                f"whoiam-{utcnow().strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}.sqlite3"
            )
            target = self.path(name)
            temporary = target.with_suffix(".partial")
            try:
                self.store.snapshot(temporary)
                metadata = {
                    **identity,
                    "created_at": utcnow().isoformat(),
                    "reason": reason,
                }
                connection = sqlite3.connect(temporary)
                try:
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS backup_info (payload TEXT NOT NULL)"
                    )
                    connection.execute("DELETE FROM backup_info")
                    connection.execute(
                        "INSERT INTO backup_info VALUES (?)", (json.dumps(metadata),)
                    )
                    connection.commit()
                finally:
                    connection.close()
                verify_database(temporary, self.store.cipher, identity)
                with temporary.open("r+b") as stream:
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                self.last_revision = self.store.revision
                self.last_time = time.monotonic()
                self.last_created = metadata["created_at"]
                self.error = False
                return {
                    "id": name,
                    "created_at": metadata["created_at"],
                    "reason": reason,
                    "size": target.stat().st_size,
                }
            finally:
                temporary.unlink(missing_ok=True)

    def maybe_create(self, force: bool = False) -> None:
        with self.store.mutex:
            if self.store.locked or self.last_revision == self.store.revision:
                return
            if not force and time.monotonic() - self.last_time < BACKUP_INTERVAL:
                return
            self.create("automatic")
            # 복원 직전의 안전 백업은 자동 삭제하지 않는다.
            rows = [row for row in self.list() if row["reason"] == "automatic"]
            for row in rows[BACKUP_KEEP:]:
                path = self.path(row["id"])
                verify_database(path, self.store.cipher, self.identity())
                path.unlink()

    def safe_backup(self, force: bool = False) -> None:
        with self.store.mutex:
            touched = self.store.touched
            try:
                self.maybe_create(force)
            except Exception:
                self.error = True
                logger.error("Local encrypted backup failed; details omitted")
            finally:
                self.store.touched = touched

    def before_lock(self) -> None:
        self.safe_backup(force=True)

    def start(self) -> None:
        def work() -> None:
            while not self.stop_event.wait(30):
                self.safe_backup()

        self.thread = threading.Thread(target=work, name="whoiam-backups", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.safe_backup(force=True)

    def restore(self, identifier: str, expected_revision: int) -> Json:
        with self.store.mutex:
            self.store.require_unlocked()
            if expected_revision != self.store.revision:
                raise DomainError(
                    "백업 목록을 연 뒤 기록이 바뀌었습니다. 새로 확인해주세요.", 409
                )
            source = self.path(identifier)
            verify_database(source, self.store.cipher, self.identity())
            safety = self.create("before-restore")
            temporary = self.vault.paths.database.with_name(
                f"restore-{uuid4().hex}.sqlite3"
            )
            try:
                shutil.copyfile(source, temporary)
                verify_database(temporary, self.store.cipher, self.identity())
                self.store.connection.close()
                self.store.connection = None
                os.replace(temporary, self.vault.paths.database)
                try:
                    self.store.connection = sqlite3.connect(
                        self.store.path, check_same_thread=False
                    )
                except Exception:
                    shutil.copyfile(self.path(safety["id"]), self.vault.paths.database)
                    self.store.connection = sqlite3.connect(
                        self.store.path, check_same_thread=False
                    )
                    raise
                self.store.revision += 1
                self.last_revision = -1
                return {"restored": True, "safety_backup": safety["id"]}
            finally:
                temporary.unlink(missing_ok=True)
