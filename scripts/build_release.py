"""Git의 검토된 파일만 골라 로컬 설치용 소스 패키지를 만든다."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

import fire

#: 기본 패키지 버전. 실행 화면과 함께 갱신한다.
VERSION = "0.04"
#: 실행에 필요한 루트 파일의 명시적 허용 목록.
ROOT_FILES = {
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "pyproject.toml",
}
#: 웹 서버가 제공하는 검토된 정적 자산.
WEB_FILES = {
    "index.html",
    "app.js",
    "report.js",
    "styles.css",
    "functional.css",
    "report.css",
    "favicon.svg",
    "README.md",
}
#: 설치·운영·경로 보호에 필요한 스크립트만 포함한다.
SCRIPT_FILES = {
    "Setup-Whoiam.ps1",
    "Start-Whoiam.ps1",
    "Install-Autostart.ps1",
    "Install-GitHooks.ps1",
    "Check-SensitivePaths.ps1",
    "Test-SensitivePaths.ps1",
    "SensitivePathPolicy.psm1",
}
#: 허용된 상위 디렉터리 안에 있어도 내보낼 수 없는 경로.
PRIVATE_PARTS = {
    ".private",
    ".git",
    ".openai",
    "__pycache__",
    ".venv",
    "node_modules",
    "data",
    "secrets",
    "credentials",
    "backups",
    "exports",
    "logs",
    "sessions",
    "uploads",
    "receipts",
}


def allowed(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if not parts or any(
        part.lower() in PRIVATE_PARTS or part in ("..", ".") for part in parts
    ):
        return False
    if path in ROOT_FILES:
        return True
    if path.startswith("apps/web/"):
        return len(parts) == 3 and parts[-1] in WEB_FILES
    if path.startswith(("apps/", "packages/")):
        return path.endswith(".py") or parts[-1] == "README.md"
    if path.startswith("scripts/"):
        return len(parts) == 2 and parts[-1] in SCRIPT_FILES
    if path.startswith("docs/"):
        return path.endswith(".md") or (
            path.startswith("docs/assets/") and path.endswith(".png")
        )
    return False


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def build(output: str = "", repository: str = "") -> dict[str, str | int]:
    root = (
        Path(repository).resolve()
        if repository
        else Path(__file__).resolve().parents[1]
    )
    target = (
        Path(output).resolve()
        if output
        else root / ".tmp" / "releases" / f"whoiam-{VERSION}.zip"
    )
    if any(part.lower() in PRIVATE_PARTS for part in target.parts):
        raise ValueError("민감 디렉터리에 패키지를 내보낼 수 없습니다.")
    if target.exists():
        raise FileExistsError(
            "기존 패키지를 덮어쓰지 않습니다. 다른 경로를 지정해주세요."
        )
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    files: dict[str, bytes] = {}
    for record in git(root, "ls-tree", "-rz", "HEAD").split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        path = raw_path.decode("utf-8")
        if not allowed(path):
            continue
        mode, kind, oid = metadata.decode().split()
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("심볼릭 링크나 외부 참조는 패키지에 포함할 수 없습니다.")
        files[path] = git(root, "cat-file", "blob", oid)
    if (
        not {"apps/server/__main__.py", "requirements.txt", "scripts/Setup-Whoiam.ps1"}
        <= files.keys()
    ):
        raise ValueError("실행에 필요한 파일이 부족합니다.")
    manifest = {
        "version": VERSION,
        "source_commit": commit,
        "files": {
            name: hashlib.sha256(value).hexdigest()
            for name, value in sorted(files.items())
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with (
        target.open("xb") as destination,
        zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for name, value in sorted(files.items()):
            archive.writestr(f"whoiam-{VERSION}/{name}", value)
        archive.writestr(
            f"whoiam-{VERSION}/MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    return {
        "archive": str(target),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "files": len(files),
        "source_commit": commit,
    }


if __name__ == "__main__":
    fire.Fire(build)
