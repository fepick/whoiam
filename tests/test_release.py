import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from scripts.build_release import build


def git(root: Path, *arguments: str, content: bytes | None = None) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], input=content, stderr=subprocess.DEVNULL
    )


def fixture_repo(root: Path) -> None:
    git(root, "init", "--quiet")
    git(root, "config", "core.hooksPath", ".git/hooks")
    git(root, "config", "user.name", "Package Test")
    git(root, "config", "user.email", "package@example.invalid")
    for name in (
        "apps/server/__main__.py",
        "requirements.txt",
        "scripts/Setup-Whoiam.ps1",
        "docs/setup.md",
        "docs/assets/demo.png",
        ".env",
        "personal-notes.txt",
        "apps/web/.openai/hosting.json",
        "packages/.private/fake.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            (
                "synthetic excluded fixture"
                if name
                in (
                    ".env",
                    "personal-notes.txt",
                    "apps/web/.openai/hosting.json",
                    "packages/.private/fake.py",
                )
                else "reviewed fixture"
            ),
            encoding="utf-8",
        )
    git(root, "add", ".")
    git(
        root,
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "Synthetic package fixture",
    )


def test_release_uses_allowlist_and_manifest_without_history(tmp_path: Path) -> None:
    fixture_repo(tmp_path)
    output = tmp_path / "release.zip"
    result = build(str(output), str(tmp_path))
    assert result["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert all(
            not any(
                part in name
                for part in (".git/", ".env", ".private/", ".openai/", "personal-notes")
            )
            for name in names
        )
        assert not any(
            b"synthetic excluded fixture" in archive.read(name) for name in names
        )
        manifest = json.loads(archive.read("whoiam-0.04/MANIFEST.json"))
        assert manifest["source_commit"] == result["source_commit"]
        for name, digest in manifest["files"].items():
            assert (
                hashlib.sha256(archive.read(f"whoiam-0.04/{name}")).hexdigest()
                == digest
            )
    with pytest.raises(FileExistsError):
        build(str(output), str(tmp_path))


def test_release_rejects_tracked_symlink_without_reading_target(tmp_path: Path) -> None:
    fixture_repo(tmp_path)
    oid = (
        git(
            tmp_path, "hash-object", "-w", "--stdin", content=b"../../never-read-target"
        )
        .decode()
        .strip()
    )
    git(
        tmp_path, "update-index", "--add", "--cacheinfo", f"120000,{oid},apps/manage.py"
    )
    git(
        tmp_path,
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "Synthetic symlink fixture",
    )
    with pytest.raises(ValueError):
        build(str(tmp_path / "release.zip"), str(tmp_path))
