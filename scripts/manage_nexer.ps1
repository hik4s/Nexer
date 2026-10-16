param([ValidateSet('start','stop','restart','status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script = Join-Path $root 'scripts\run_local.py'
$apiUrl = 'http://127.0.0.1:8000/health'
function Get-LocalApi {
    $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @('127.0.0.1','::1') } | Select-Object -First 1
    if (-not $listener) { return $null }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if (-not $process) { throw 'Processo da porta 8000 não encontrado.' }
    $command = [string]$process.CommandLine
    if (-not $command.Contains($script) -or -not $command.Contains('--api-only')) {
        throw "Porta 8000 ocupada por outro processo (PID $($process.ProcessId)). Nenhum processo foi encerrado."
    }
    return $process
}
function Wait-Api([bool]$shouldBeOnline) {
    for ($i=0; $i -lt 80; $i++) {
        $online = $null -ne (Get-LocalApi)
        if ($online -eq $shouldBeOnline) { return }
        Start-Sleep -Milliseconds 250
    }
    throw 'Tempo limite aguardando alteração de estado da API.'
}
if ($Action -eq 'status') {
    if (Get-LocalApi) { Write-Output 'API_RUNNING' } else { Write-Output 'API_STOPPED' }
    exit 0
}
# Refuse a partial restart: the desktop button starts API and dashboard together.
# Missing frontend packages must be repaired explicitly, without touching an active API.
if ($Action -in @('start','restart')) {
    $viteScript = Join-Path $root 'apps\frontend\node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $viteScript -PathType Leaf)) {
        throw 'Interface nao preparada. Abra Preparar-Frontend-Nexer.cmd na pasta do Nexer. A API existente nao foi interrompida.'
    }
}
if ($Action -in @('stop','restart')) {
    $api = Get-LocalApi
    if ($api) {
        # Only stop the verified local API-only process for this project.
        Stop-Process -Id $api.ProcessId -ErrorAction Stop
        Wait-Api $false
        Write-Output 'API_STOPPED'
    } else { Write-Output 'API_ALREADY_STOPPED' }
}
if ($Action -in @('start','restart')) {
    & (Join-Path $PSScriptRoot 'open_nexer.ps1') -NoBrowser
    Wait-Api $true
    Write-Output 'API_RUNNING'
}
