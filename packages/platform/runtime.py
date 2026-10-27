"""개발 checkout과 분리된 실행 프로필 및 단일 실행 경계."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from packages.platform.domain import DomainError

#: 운영 데이터는 개발 저장소 밖의 사용자 전용 경로에 보관한다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("production", "development", "test")


@dataclass(frozen=True)
class RuntimePaths:
    profile: str
    root: Path

    @property
    def database(self) -> Path:
        return self.root / "database" / "whoiam.sqlite3"

    @property
    def manifest(self) -> Path:
        return self.root / "vault.json"

    @property
    def backups(self) -> Path:
        return self.root / "backups"


def runtime_paths(profile: str = "production", data_home: str = "") -> RuntimePaths:
    if profile not in PROFILES:
        raise DomainError("production·development·test 중 실행 프로필을 선택해주세요.")
    if data_home:
        home = Path(data_home).expanduser()
        if not home.is_absolute():
            raise DomainError("데이터 홈은 절대 경로로 지정해주세요.")
        home = home.resolve()
    elif profile == "production":
        base = (
            os.environ.get("LOCALAPPDATA")
            if os.name == "nt"
            else os.environ.get("XDG_DATA_HOME")
        )
        if os.name == "nt" and not base:
            raise DomainError("사용자 로컬 데이터 경로가 필요합니다.")
        home = (
            Path(base) / "Whoiam"
            if base
            else Path.home() / ".local" / "share" / "Whoiam"
        )
    elif profile == "development":
        home = PROJECT_ROOT
    else:
        raise DomainError("test 프로필에는 임시 data_home을 명시해주세요.")
    if profile == "production" and home.is_relative_to(PROJECT_ROOT):
        raise DomainError("운영 데이터 홈은 개발 저장소 밖으로 지정해주세요.")
    return RuntimePaths(profile, home / ".private" / profile)


def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise DomainError("보호 디렉터리에 심볼릭 링크를 사용할 수 없습니다.")
    if os.name == "nt":
        try:
            from packages.platform.permissions import restrict_windows

            restrict_windows(path)
        except Exception:
            raise DomainError(
                "사용자 전용 디렉터리 권한 설정에 실패했습니다.", 503
            ) from None
    elif os.name != "nt":
        if path.stat().st_uid != os.getuid():
            raise DomainError("다른 사용자의 데이터 디렉터리는 열 수 없습니다.", 403)
        path.chmod(0o700)


def write_new_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        if os.name != "nt":
            path.chmod(0o600)
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())


class InstanceLock:
    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self.stream: IO[bytes] | None = None

    def acquire(self) -> None:
        private_directory(self.paths.root)
        self.stream = (self.paths.root / "instance.lock").open("a+b")
        try:
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt

                if self.stream.read(1) == b"":
                    self.stream.write(b"0")
                    self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            self.stream = None
            raise DomainError(
                "이 프로필은 이미 실행 중입니다. 기존 창을 사용해주세요.", 409
            ) from None

    def release(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
