# Keep the offline operator environment separate from Django's import environment.
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
    & uv run --project $PSScriptRoot python "$PSScriptRoot/manage.py" @importArguments
    exit $LASTEXITCODE
}
& uv run --project "$PSScriptRoot/operator-tools" kpopwins-operator @args
exit $LASTEXITCODE
