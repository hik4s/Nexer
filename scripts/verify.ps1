param(
    [switch]$SkipAudit
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

Write-Host "== RelatPy verification =="
Write-Host "Branch: $((git branch --show-current).Trim())"
Write-Host "Commit: $((git rev-parse HEAD).Trim())"

Invoke-Checked python -m pip check

$env:PYTHONPATH = "$root\apps\backend;$root\apps\worker;$root\apps\runtime"
Invoke-Checked python -m unittest discover -s apps\backend\tests -v

$env:PYTHONPATH = "$root\apps\worker;$root\apps\backend;$root\apps\runtime"
Invoke-Checked python -m unittest discover -s apps\worker\tests -v

$env:PYTHONPATH = "$root\apps\runtime"
Invoke-Checked python -m unittest discover -s apps\runtime\tests -v

Push-Location apps\frontend
try {
    Invoke-Checked npm install --no-audit --no-fund
    Invoke-Checked npm test
    Invoke-Checked npm run typecheck
    Invoke-Checked npm run build
} finally {
    Pop-Location
}

if (-not $SkipAudit) {
    Invoke-Checked python -m pip install pip-audit
    Invoke-Checked python -m pip_audit -r Requisitos.txt -r apps\backend\requirements.txt -r apps\runtime\requirements.txt

    Push-Location apps\frontend
    try {
        Invoke-Checked npm audit --audit-level=high
    } finally {
        Pop-Location
    }
}

Write-Host "== RelatPy verification passed =="
