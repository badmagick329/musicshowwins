import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "command,code,expected",
    [
        (
            "review batch --limit 10",
            7,
            ["kpopwins-operator", "review", "batch", "--limit", "10"],
        ),
        (
            'verify "C:/folder with spaces/references.json"',
            0,
            [
                "import_win_references",
                "C:/folder with spaces/references.json",
                "--dry-run",
            ],
        ),
        (
            'import "C:/folder with spaces/references.json"',
            0,
            ["import_win_references", "C:/folder with spaces/references.json"],
        ),
    ],
)
def test_launcher_routes_arguments_and_exit_codes_without_running_uv(
    command, code, expected
):
    shell = shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell is not installed")
    launcher = Path(__file__).resolve().parents[2] / "operator.ps1"
    script = (
        "function uv { ConvertTo-Json -InputObject "
        "@($args | ForEach-Object { [string]$_ }) -Compress; "
        f"$global:LASTEXITCODE = {code} }}; "
        f"& '{str(launcher).replace(chr(39), chr(39) * 2)}' {command}; "
        "exit $LASTEXITCODE"
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == code, result.stderr
    arguments = json.loads(result.stdout)
    assert arguments[-len(expected) :] == expected
