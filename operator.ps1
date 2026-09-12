# Keep the offline operator environment separate from Django's import environment.
$localApi = if ($env:KPOPWINS_LOCAL_API_BASE_URL) {
    $env:KPOPWINS_LOCAL_API_BASE_URL
} else { 'http://127.0.0.1:8000/api/v1' }
if ($args.Count -gt 0 -and $args[0] -in @('sync-local', 'prepare', 'refresh-wins') -and
    -not ($args[0] -eq 'prepare' -and ($args -contains '--help' -or $args -contains '-h'))) {
    $apiUri = $null
    if (-not [Uri]::TryCreate($localApi, [UriKind]::Absolute, [ref]$apiUri) -or
        $apiUri.Scheme -notin @('http', 'https') -or -not $apiUri.IsLoopback) {
        Write-Error 'KPOPWINS_LOCAL_API_BASE_URL must be a local HTTP API URL.'
        exit 2
    }
    Write-Host "Catalogue source: $localApi; target: local Django (repository settings)."
    if ($args[0] -in @('sync-local', 'prepare')) {
        Write-Host 'Synchronizing local Django wins from Wikipedia before discovery.'
        $syncArguments = @('sync_wikipedia', '--skip-cache-refresh')
        if ($args[0] -eq 'sync-local' -and $args.Count -gt 1) {
            $syncArguments += $args[1..($args.Count - 1)]
        }
        & uv run --project $PSScriptRoot python "$PSScriptRoot/manage.py" @syncArguments
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        if ($args[0] -eq 'sync-local') { exit 0 }
    }
    $previousApi = $env:KPOPWINS_API_BASE_URL
    try {
        $env:KPOPWINS_API_BASE_URL = $localApi
        & uv run --project "$PSScriptRoot/operator-tools" kpopwins-operator @args
        $operatorExitCode = $LASTEXITCODE
    } finally {
        $env:KPOPWINS_API_BASE_URL = $previousApi
    }
    exit $operatorExitCode
}
if ($args.Count -gt 0 -and $args[0] -in @('verify', 'import')) {
    if ($args.Count -gt 2) {
        Write-Error 'Usage: ./operator.ps1 verify|import [manifest-path]'
        exit 2
    }
    $manifestPath = if ($args.Count -eq 2) { $args[1] } else {
        $operatorHome = if ($env:KPOPWINS_OPERATOR_HOME) {
            $env:KPOPWINS_OPERATOR_HOME
        } else { Join-Path $PSScriptRoot '.ignore/operator-tools' }
        Join-Path $operatorHome 'manifests/win-references-v1.json'
    }
    $importArguments = @('import_win_references', $manifestPath)
    if ($args[0] -eq 'verify') { $importArguments += '--dry-run' }
    Write-Host "Expected catalogue source for this workflow: $localApi"
    Write-Host 'Target: local Django (repository settings). Verify is a dry run; import writes references.'
    & uv run --project $PSScriptRoot python "$PSScriptRoot/manage.py" @importArguments
    $importExitCode = $LASTEXITCODE
    if ($importExitCode -eq 0 -and $args[0] -eq 'verify') {
        Write-Host "Next: ./operator.ps1 import `"$manifestPath`""
    }
    exit $importExitCode
}
& uv run --project "$PSScriptRoot/operator-tools" kpopwins-operator @args
exit $LASTEXITCODE
