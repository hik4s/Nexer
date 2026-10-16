param(
    [ValidateRange(1, 65535)][int]$ApiPort = 8000,
    [ValidateRange(1, 65535)][int]$FrontendPort = 5173,
    [ValidateRange(1, 120)][int]$StartupTimeoutSeconds = 45,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot 'apps\frontend'
$apiUrl = "http://127.0.0.1:$ApiPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"

function Test-NexerReady {
    param([string]$Uri, [switch]$Api)
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 1
        if ($response.StatusCode -ne 200) { return $false }
        if ($Api) { return (($response.Content | ConvertFrom-Json).api -like 'Nexer*') }
        return ($response.Content -match '<title>Nexer' -and $response.Content -match 'id="root"')
    } catch { return $false }
}

function Assert-NexerPortFree {
    param([int]$Port)
    $connection = New-Object System.Net.Sockets.TcpClient
    try {
        $attempt = $connection.BeginConnect('127.0.0.1', $Port, $null, $null)
        if ($attempt.AsyncWaitHandle.WaitOne(500)) {
            try { $connection.EndConnect($attempt) } catch { return }
            throw "Port $Port is occupied by another service. Close it or choose another port."
        }
    } finally { $connection.Dispose() }
}

function Wait-NexerReady {
    param([string]$Uri, $Process, [switch]$Api)
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    do {
        if (Test-NexerReady -Uri $Uri -Api:$Api) { return }
        if ($Process.HasExited) { throw 'Nexer failed to start. Check the installed Python/Node dependencies.' }
        Start-Sleep -Milliseconds 300
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Nexer startup timed out. The launcher does not install dependencies or modify the database.'
}

# Check the frontend before starting any new API process, so missing packages never
# leave the program partially launched. Setup is intentionally a visible one-time action.
$viteScript = Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $viteScript -PathType Leaf) -and -not (Test-NexerReady -Uri $frontendUrl)) {
    throw 'Interface do Nexer nao preparada. Execute Preparar-Frontend-Nexer.cmd na pasta do projeto e tente novamente. A API nao foi reiniciada.'
}

if (-not (Test-NexerReady -Uri "$apiUrl/version" -Api)) {
    Assert-NexerPortFree -Port $ApiPort
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = Join-Path $projectRoot 'venv\Scripts\python.exe' }
    $pythonArguments = ''
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        $pythonPath = (Get-Command py.exe -ErrorAction Stop).Source
        $pythonArguments = '-3.12 '
    }
    $runScript = Join-Path $projectRoot 'scripts\run_local.py'
    $previousDisplay = $env:NEXER_PAIRING_CODE_DISPLAY
    $previousPort = $env:NEXER_PORT
    $previousOrigins = $env:NEXER_CORS_ORIGINS
    try {
        $env:NEXER_PAIRING_CODE_DISPLAY = 'window'
        $env:NEXER_PORT = "$ApiPort"
        $env:NEXER_CORS_ORIGINS = ConvertTo-Json -Compress -InputObject @($frontendUrl, "http://localhost:$FrontendPort")
        $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList "$pythonArguments`"$runScript`" --api-only" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    } finally {
        $env:NEXER_PAIRING_CODE_DISPLAY = $previousDisplay
        $env:NEXER_PORT = $previousPort
        $env:NEXER_CORS_ORIGINS = $previousOrigins
    }
    Wait-NexerReady -Uri "$apiUrl/version" -Process $apiProcess -Api
}

if (-not (Test-NexerReady -Uri $frontendUrl)) {
    Assert-NexerPortFree -Port $FrontendPort
    if (-not (Test-Path -LiteralPath $viteScript -PathType Leaf)) {
        throw 'Interface do Nexer nao preparada. Execute Preparar-Frontend-Nexer.cmd e tente novamente.'
    }
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
    $previousApiUrl = $env:VITE_API_URL
    try {
        $env:VITE_API_URL = $apiUrl
        $frontendProcess = Start-Process -FilePath $nodePath -ArgumentList "`"$viteScript`" --host 127.0.0.1 --port $FrontendPort --strictPort" -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru
    } finally { $env:VITE_API_URL = $previousApiUrl }
    Wait-NexerReady -Uri $frontendUrl -Process $frontendProcess
}

if (-not $NoBrowser) { Start-Process -FilePath $frontendUrl -WindowStyle Hidden }
Write-Host "Nexer: $frontendUrl"
Write-Host 'Voce pode fechar este terminal. O Nexer continua em segundo plano.'
