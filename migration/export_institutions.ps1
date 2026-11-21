param(
    [string]$Container = "docker-db-1",
    [string]$Database = "gerijatrija_dbmain",
    [string]$Output = ".\migration\institutions_export.csv"
)

$ErrorActionPreference = "Stop"

if (Test-Path -LiteralPath $Output) {
    throw "Export blocked: file already exists: $Output"
}

$csv = & docker exec $Container psql `
    -X -v ON_ERROR_STOP=1 `
    -U odoo -d $Database `
    -c "\copy (SELECT id AS legacy_id FROM res_partner WHERE is_institution IS TRUE ORDER BY id) TO STDOUT WITH CSV HEADER"

if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL export failed. Exit code: $LASTEXITCODE"
}

if (-not $csv -or $csv[0].Trim() -ne "legacy_id") {
    throw "Invalid CSV export"
}

$encoding = New-Object System.Text.UTF8Encoding($false)

$fullPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Output)

[System.IO.File]::WriteAllLines(
    $fullPath,
    [string[]]$csv,
    $encoding
)

Write-Host "SOURCE DATABASE: $Database"
Write-Host "INSTITUTIONS EXPORTED: $($csv.Count - 1)"
Write-Host "OUTPUT: $Output"
