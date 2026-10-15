#requires -version 5.1
[CmdletBinding()]
param(
    [switch]$NoLaunch,
    # Compatibilidade com verificacoes antigas: agora equivale a -NoLaunch.
    [switch]$SkipAuthSetup,
    [switch]$SkipDependencies,
    [switch]$UpgradeExistingDatabase
)

$ErrorActionPreference = 'Stop'
if ($SkipAuthSetup) {
    Write-Warning '-SkipAuthSetup obsoleto: use -NoLaunch. O acesso atual usa codigo de pareamento.'
    $NoLaunch = $true
}
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'apps\frontend'
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$database = Join-Path $root 'data\nexer.db'
$settingsFile = Join-Path $root '.env'

function Assert-Exists([string]$path, [string]$description) {
    if (-not (Test-Path -LiteralPath $path)) { throw "$description ausente: $path" }
}

function Invoke-Checked([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "Comando falhou (exit $LASTEXITCODE): $program" }
}

function Assert-NodeVersion {
    $version = (& node.exe --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^v(\d+)\.(\d+)\.') {
        throw 'Node.js nao encontrado ou versao invalida.'
    }
    $major = [int]$Matches[1]; $minor = [int]$Matches[2]
    if (-not (($major -eq 20 -and $minor -ge 19) -or ($major -eq 22 -and $minor -ge 12) -or ($major -ge 24))) {
        throw 'O frontend exige Node 20.19+, 22.12+ ou 24+.'
    }
}

try {
    if ([Environment]::OSVersion.Platform -ne 'Win32NT') {
        throw 'Este instalador requer Windows.'
    }

    foreach ($relative in @(
        'scripts\run_local.py',
        'scripts\open_nexer.ps1', 'apps\worker\requirements.txt',
        'apps\frontend\package.json', 'apps\frontend\package-lock.json',
        'apps\backend\alembic.ini', 'apps\backend\alembic\env.py',
        'scripts\requirements-windows-py312.lock.txt'
    )) { Assert-Exists (Join-Path $root $relative) $relative }

    # Nao atualizar um banco trazido de outro checkout ou uma instalacao ja existente.
    if ($env:NEXER_DATABASE_URL) {
        throw 'NEXER_DATABASE_URL definido no ambiente. Use a instalacao documentada para seu banco especifico.'
    }
    if (Test-Path -LiteralPath $settingsFile) {
        $customDb = @(Get-Content -LiteralPath $settingsFile | Where-Object { $_ -match '^\s*NEXER_DATABASE_URL\s*=' })
        if ($customDb.Count -gt 0) {
            throw 'Banco personalizado no .env; instalador nao executara migrations nesse banco.'
        }
    }
    if (Test-Path -LiteralPath (Join-Path $root '.git')) {
        $git = Get-Command git.exe -ErrorAction SilentlyContinue
        if (-not $git) { throw 'Git necessario para conferir se banco local foi versionado.' }
        $trackedDb = @(& $git.Source -C $root ls-files -- 'data/nexer.db')
        if ($trackedDb.Count -gt 0) {
            throw 'data/nexer.db ainda rastreado pelo Git. Remova do indice antes de distribuir, preservando o arquivo local.'
        }
    }
    if ((Test-Path -LiteralPath $database) -and -not $UpgradeExistingDatabase) {
        throw 'data/nexer.db ja existe. Nenhum dado foi alterado; para uma atualizacao consciente use -UpgradeExistingDatabase.'
    }

    if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
        throw 'Python Launcher nao encontrado. Instale Python 3.12 e o comando py.'
    }
    Invoke-Checked 'py.exe' @('-3.12', '--version')
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
        throw 'Node.js ausente. Instale Node.js 22 LTS ou 24+.'
    }
    Assert-NodeVersion
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'npm.cmd ausente. Instale Node.js com npm.'
    }

    if (-not (Test-Path -LiteralPath $python)) {
        if (Test-Path -LiteralPath $venv) {
            throw 'Ambiente .venv incompleto. Corrija manualmente; o instalador nao apaga arquivos.'
        }
        Write-Host '[1/5] Criando ambiente Python isolado...'
        Invoke-Checked 'py.exe' @('-3.12', '-m', 'venv', $venv)
    } else { Write-Host '[1/5] Ambiente Python ja existe.' }
    Assert-Exists $python 'Interpretador Python da .venv'

    if (-not $SkipDependencies) {
        Write-Host '[2/5] Instalando dependencias Python/Node do projeto...'
        Invoke-Checked $python @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $root 'apps\worker\requirements.txt'), '-c', (Join-Path $root 'scripts\requirements-windows-py312.lock.txt'))
        Invoke-Checked $python @('-m', 'pip', 'check')
        Invoke-Checked 'npm.cmd' @('ci', '--prefix', $frontend, '--no-audit', '--no-fund')
    } else {
        Write-Host '[2/5] Dependencias omitidas (somente verificacao controlada).'
        Assert-Exists (Join-Path $frontend 'node_modules\vite\bin\vite.js') 'Vite'
        Invoke-Checked $python @('-c', 'import fastapi, sqlalchemy, alembic, playwright, uvicorn')
    }

    Write-Host '[3/5] Inicializando banco SQLite com migrations...'
    $previous = Get-Location
    try {
        Set-Location $root
        if (-not (Test-Path -LiteralPath (Join-Path $root 'data'))) {
            New-Item -Path (Join-Path $root 'data') -ItemType Directory -Force | Out-Null
        }
        Invoke-Checked $python @('-m', 'alembic', '-c', (Join-Path $root 'apps\backend\alembic.ini'), 'upgrade', 'head')
    } finally { Set-Location $previous }

    Write-Host '[4/5] Acesso local por codigo de pareamento, emitido ao abrir o Nexer.'

    Write-Host '[5/5] Instalacao local concluida.'
    if (-not $NoLaunch) {
        if ($env:NEXER_ENVIRONMENT -eq 'test') { throw 'NEXER_ENVIRONMENT=test nao permitido para inicializacao normal.' }
        $occupied = @(Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue)
        if ($occupied.Count -gt 0) {
            throw 'Portas 8000/5173 ocupadas. Instalacao concluida; nao foi iniciado outro Nexer.'
        }
        # Launcher so inicia API e frontend, nunca consome fila anterior automaticamente.
        & (Join-Path $root 'scripts\open_nexer.ps1')
        if (-not $?) { throw 'Falha ao iniciar Nexer.' }
    } else {
        Write-Host 'Nenhum servidor ou worker iniciado (-NoLaunch).'
    }
    exit 0
} catch {
    Write-Error ("Instalacao interrompida: " + $_.Exception.Message)
    exit 1
}
