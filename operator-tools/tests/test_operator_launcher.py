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
    arguments = next(
        json.loads(line) for line in result.stdout.splitlines() if line.startswith("[")
    )
    assert arguments[-len(expected) :] == expected
    if command.startswith("verify"):
        assert (
            'Next: ./operator.ps1 import "C:/folder with spaces/references.json"'
            in result.stdout
        )


@pytest.mark.parametrize("sync_code", [0, 9])
def test_prepare_syncs_first_and_stops_on_sync_failure(sync_code):
    shell = shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell is not installed")
    launcher = Path(__file__).resolve().parents[2] / "operator.ps1"
    script = (
        "$env:KPOPWINS_API_BASE_URL = 'https://api.kpopwins.info/api/v1'; "
        "$env:KPOPWINS_LOCAL_API_BASE_URL = 'http://127.0.0.1:8123/api/v1'; "
        "function uv { ConvertTo-Json -InputObject "
        "@{arguments=@($args | ForEach-Object { [string]$_ }); "
        "source=$env:KPOPWINS_API_BASE_URL} -Compress; "
        "if ($args -contains 'sync_wikipedia') { "
        f"$global:LASTEXITCODE = {sync_code} }} "
        "else { $global:LASTEXITCODE = 0 } }; "
        f"& '{str(launcher).replace(chr(39), chr(39) * 2)}' prepare --reddit; "
        "$resultCode = $LASTEXITCODE; "
        "Write-Output ('RESTORED=' + $env:KPOPWINS_API_BASE_URL); exit $resultCode"
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-Command", script], capture_output=True, text=True
    )
    assert result.returncode == sync_code, result.stderr
    calls = [
        json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")
    ]
    assert calls[0]["arguments"][-2:] == ["sync_wikipedia", "--skip-cache-refresh"]
    assert len(calls) == (1 if sync_code else 2)
    if not sync_code:
        assert calls[1]["arguments"][-3:] == [
            "kpopwins-operator",
            "prepare",
            "--reddit",
        ]
        assert calls[1]["source"] == "http://127.0.0.1:8123/api/v1"
        assert "RESTORED=https://api.kpopwins.info/api/v1" in result.stdout
