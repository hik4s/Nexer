param(
    [switch]$SkipAudit
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== RelatPy verification =="
Write-Host "Branch: $((git branch --show-current).Trim())"
Write-Host "Commit: $((git rev-parse HEAD).Trim())"

python -m pip check

$env:PYTHONPATH = "$root\apps\backend"
python -m unittest discover -s apps\backend\tests -v

$env:PYTHONPATH = "$root\apps\worker;$root\apps\backend;$root\apps\runtime"
python -m unittest discover -s apps\worker\tests -v

$env:PYTHONPATH = "$root\apps\runtime"
python -m unittest discover -s apps\runtime\tests -v

Push-Location apps\frontend
try {
    npm test
    npm run typecheck
    npm run build
} finally {
    Pop-Location
}

if (-not $SkipAudit) {
    python -m pip install pip-audit
    python -m pip_audit -r Requisitos.txt -r apps\backend\requirements.txt -r apps\runtime\requirements.txt
    Push-Location apps\frontend
    try {
        npm audit --audit-level=high
    } finally {
        Pop-Location
    }
}

Write-Host "== RelatPy verification passed =="
