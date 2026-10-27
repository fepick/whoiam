"""현재 사용자로 실행하는 Windows 로그인 작업의 제한된 어댑터."""

import json
import os
import subprocess

from packages.platform.domain import DomainError, Json
from packages.platform.runtime import PROJECT_ROOT


class Autostart:
    def __init__(self, profile: str, port: int, data_home: str = "") -> None:
        self.profile, self.port, self.data_home = profile, port, data_home

    def invoke(self, option: str = "") -> str:
        if os.name != "nt" or self.profile not in ("production", "development"):
            raise DomainError("자동 실행은 Windows 운영·개발 프로필에서 지원합니다.")
        shell = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32",
            "WindowsPowerShell",
            "v1.0",
            "powershell.exe",
        )
        arguments = [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(PROJECT_ROOT / "scripts" / "Install-Autostart.ps1"),
            "-Profile",
            self.profile,
            "-Port",
            str(self.port),
        ]
        if self.data_home:
            arguments.extend(["-DataHome", self.data_home])
        if option:
            arguments.append(option)
        try:
            result = subprocess.run(
                arguments,
                capture_output=True,
                check=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.stdout.decode("utf-8-sig").strip()
        except Exception:
            raise DomainError(
                "로그인 자동 실행 설정에 실패했습니다. 실행 환경과 사내 정책을 확인해주세요.",
                503,
            ) from None

    def status(self) -> Json:
        return json.loads(self.invoke("-Status"))

    def set(self, enabled: bool) -> Json:
        if type(enabled) is not bool:
            raise DomainError("자동 실행 설정값을 확인해주세요.")
        self.invoke("" if enabled else "-Remove")
        return self.status()
