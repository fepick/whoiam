"""로컬 버전과 공개 GitHub 릴리스의 비교 및 메모리 캐시."""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from packages.platform.domain import Json

#: 로컬 배포 버전은 Git checkout과 설치 ZIP에서 같은 파일을 사용한다.
VERSION = (
    (Path(__file__).resolve().parents[2] / "VERSION")
    .read_text(encoding="utf-8")
    .strip()
)
#: 공개 릴리스 메타데이터만 조회하는 고정 목적지.
RELEASE_API = "https://api.github.com/repos/fepick/whoiam/releases/latest"
#: 원격 응답의 최대 크기.
MAX_RELEASE_BYTES = 1024 * 1024
#: 정상 확인과 실패 후 자동 재시도 간격(초).
CHECK_INTERVAL = 24 * 60 * 60
ERROR_INTERVAL = 60 * 60
#: 수동 확인을 연속 실행할 때의 최소 간격(초).
MANUAL_INTERVAL = 60


def version_parts(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d{1,6})\.(\d{1,6})(?:\.(\d{1,6}))?", value)
    if not match:
        raise ValueError("지원하지 않는 버전 형식입니다.")
    return tuple(int(part or 0) for part in match.groups())


def latest_release() -> Json:
    request = Request(
        RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "whoiam-update-check",
        },
    )
    with urlopen(request, timeout=5) as response:
        payload = response.read(MAX_RELEASE_BYTES + 1)
    if len(payload) > MAX_RELEASE_BYTES:
        raise ValueError("릴리스 응답이 너무 큽니다.")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("릴리스 형식을 확인해주세요.")
    return value


class Updates:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_check = 0.0
        self.last_attempt = float("-inf")
        self.state: Json = {
            "current_version": VERSION,
            "latest_version": "",
            "available": False,
            "status": "unchecked",
            "checked_at": "",
            "release_url": "",
        }

    def status(self, check: bool = False, force: bool = False) -> Json:
        with self.lock:
            now = time.monotonic()
            due = force and now - self.last_attempt >= MANUAL_INTERVAL
            if (
                check
                and self.state["status"] != "checking"
                and (due or now >= self.next_check)
            ):
                self.last_attempt = now
                self.state["status"] = "checking"
                threading.Thread(target=self.check, daemon=True).start()
            return dict(self.state)

    def check(self) -> None:
        result: Json = {"status": "error"}
        interval = ERROR_INTERVAL
        try:
            release = latest_release()
            tag = release.get("tag_name")
            if (
                release.get("draft")
                or release.get("prerelease")
                or not isinstance(tag, str)
            ):
                raise ValueError("정식 릴리스가 아닙니다.")
            remote = version_parts(tag)
            result = {
                "status": "ok",
                "latest_version": tag.removeprefix("v"),
                "available": remote > version_parts(VERSION),
                "release_url": "https://github.com/fepick/whoiam/releases/tag/"
                + quote(tag, safe=""),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            interval = CHECK_INTERVAL
        except HTTPError as error:
            if error.code == 404:
                result = {
                    "status": "no_release",
                    "available": False,
                    "latest_version": "",
                    "release_url": "",
                }
                interval = CHECK_INTERVAL
        except Exception:
            pass
        with self.lock:
            self.state.update(result)
            self.next_check = time.monotonic() + interval
