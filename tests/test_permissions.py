import base64
import json
import os
import subprocess
from pathlib import Path

import pytest

from packages.platform.runtime import private_directory


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL validation")
def test_private_directory_has_only_current_user_and_system(tmp_path: Path) -> None:
    directory = tmp_path / "synthetic-private-permissions"
    private_directory(directory)
    script = """
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:WHOIAM_TEST_DIRECTORY
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
$unexpected = @($rules | Where-Object { $_.IdentityReference.Value -notin @($sid, 'S-1-5-18') }).Count
@{protected=$acl.AreAccessRulesProtected; entries=$rules.Count; unexpected=$unexpected} | ConvertTo-Json -Compress
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        env={**os.environ, "WHOIAM_TEST_DIRECTORY": str(directory)},
        capture_output=True,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    verified = json.loads(result.stdout.decode("utf-8-sig"))
    assert verified == {"protected": True, "entries": 2, "unexpected": 0}
