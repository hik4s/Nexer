#requires -version 5.1
[CmdletBinding()]
param([switch]$Reinstall)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'apps\frontend'
$manifest = Join-Path $frontend 'package.json'
$lockfile = Join-Path $frontend 'package-lock.json'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'

try {
    foreach ($required in @($manifest, $lockfile)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Arquivo de instalacao do frontend ausente: $required"
        }
    }
    if ((Test-Path -LiteralPath $vite -PathType Leaf) -and -not $Reinstall) {
        Write-Host '[OK] Interface do Nexer ja preparada; nenhum pacote foi alterado.'
        exit 0
    }
    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $node -or -not $npm) {
        throw 'Node.js e npm nao encontrados. Instale Node.js 22 LTS ou 24+ e execute este arquivo novamente.'
    }
    $version = (& $node.Source --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^v(\d+)\.(\d+)\.') {
        throw 'Nao foi possivel verificar a versao do Node.js.'
    }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if (-not (($major -eq 20 -and $minor -ge 19) -or ($major -eq 22 -and $minor -ge 12) -or ($major -ge 24))) {
        throw 'Node.js incompatível. Use 20.19+, 22.12+ ou 24+.'
    }
    Write-Host '[Nexer] Preparando frontend com as versoes do package-lock.json...'
    Write-Host 'Aguarde a instalacao. Nenhum banco, credencial, API ou worker sera alterado.'
    & $npm.Source ci --prefix $frontend --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci falhou (exit $LASTEXITCODE). Confira rede, proxy e permissao do npm."
    }
    if (-not (Test-Path -LiteralPath $vite -PathType Leaf)) {
        throw 'npm finalizou, mas Vite nao foi encontrado. Revise a instalacao do Node/npm.'
    }
    Write-Host '[OK] Interface preparada. Agora abra o Nexer normalmente.'
    exit 0
} catch {
    Write-Error ("Preparacao do frontend interrompida: " + $_.Exception.Message)
    exit 1
}
