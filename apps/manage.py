"""운영 관리 CLI. 실제 자료는 사용자가 명시한 작업에서만 연다."""

from __future__ import annotations

import getpass
import os
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

import fire
from cryptography.fernet import Fernet
from loguru import logger

from packages.platform.backups import Backups, readonly, verify_database
from packages.platform.domain import DomainError, Json
from packages.platform.keys import os_key
from packages.platform.recovery import export_recovery, read_recovery, recover_backup
from packages.platform.runtime import (
    PROJECT_ROOT,
    InstanceLock,
    private_directory,
    runtime_paths,
)
from packages.platform.storage import EncryptedStore
from packages.platform.vault import Vault


def recovery_password(confirm: bool = False) -> str:
    password = getpass.getpass("복구 암호 (12자 이상): ")
    if confirm and getpass.getpass("복구 암호 확인: ") != password:
        raise DomainError("복구 암호가 일치하지 않습니다.")
    return password


class Manage:
    def backup(self, profile: str = "production", data_home: str = "") -> None:
        paths = runtime_paths(profile, data_home)
        lock = InstanceLock(paths)
        lock.acquire()
        store = None
        try:
            vault = Vault(paths)
            vault.existing_identity()
            store = EncryptedStore(paths.database, vault.load_key)
            store.unlock()
            Backups(store, vault).create()
            logger.info("암호화 백업을 만들고 검증했습니다.")
        finally:
            if store:
                store.close()
            lock.release()

    def export_recovery(
        self, destination: str, profile: str = "production", data_home: str = ""
    ) -> None:
        paths = runtime_paths(profile, data_home)
        lock = InstanceLock(paths)
        lock.acquire()
        try:
            export_recovery(
                Vault(paths), Path(destination), recovery_password(confirm=True)
            )
            logger.info(
                "암호화 복구 파일을 만들었습니다. 복구 암호는 파일과 따로 보관해주세요."
            )
        finally:
            lock.release()

    def recover(
        self,
        backup: str,
        recovery_file: str,
        profile: str = "production",
        data_home: str = "",
    ) -> None:
        paths = runtime_paths(profile, data_home)
        lock = InstanceLock(paths)
        lock.acquire()
        try:
            identity, key = read_recovery(Path(recovery_file), recovery_password())
            recover_backup(Vault(paths), Path(backup), identity, key)
            logger.info("빈 데이터 홈에 복구했습니다. 앱을 실행해 내용을 확인해주세요.")
        finally:
            lock.release()

    def migrate_legacy(self, profile: str = "production", data_home: str = "") -> None:
        paths = runtime_paths(profile, data_home)
        lock = InstanceLock(paths)
        lock.acquire()
        try:
            source = PROJECT_ROOT / ".private" / "database" / "whoiam.sqlite3"
            migrate_legacy(source, Vault(paths))
            logger.info(
                "기존 저장소를 새 프로필에 복사·검증했습니다. 원본과 기존 키는 보존했습니다."
            )
        finally:
            lock.release()


def migrate_legacy(source: Path, vault: Vault, legacy_key: bytes | None = None) -> None:
    if not source.is_file():
        raise DomainError("이전할 기존 저장소가 없습니다.")
    if vault.paths.database.exists() or vault.paths.manifest.exists():
        raise DomainError(
            "이전 대상은 비어 있어야 합니다. 기존 데이터를 덮어쓰지 않습니다.", 409
        )
    key = legacy_key if legacy_key is not None else os_key(source)
    verify_database(source, Fernet(key))
    private_directory(vault.paths.root)
    private_directory(vault.paths.database.parent)
    temporary = vault.paths.database.with_name(f"migration-{uuid4().hex}.sqlite3")
    try:
        incoming, target = readonly(source), sqlite3.connect(temporary)
        try:
            incoming.backup(target)
        finally:
            incoming.close()
            target.close()
        verify_database(temporary, Fernet(key))
        vault.initialize(key)
        os.replace(temporary, vault.paths.database)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, format="{level}: {message}", diagnose=False, backtrace=False)
    try:
        fire.Fire(Manage)
    except DomainError as error:
        logger.error(str(error))
        raise SystemExit(1) from None
    except Exception:
        logger.error(
            "관리 작업에 실패했습니다. 입력과 OS 저장소 상태를 확인해주세요. 원문은 출력하지 않습니다."
        )
        raise SystemExit(1) from None
