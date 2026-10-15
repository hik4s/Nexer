"""Launch orchestration tests with mocked HTTP/process boundaries; no services."""
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenNexerTests(unittest.TestCase):
    def run_harness(self, *, reuse):
        launcher = str(ROOT / "scripts/open_nexer.ps1").replace("'", "''")
        harness = r'''
$ErrorActionPreference = 'Stop'
$script:launched = @()
$script:reuse = REUSE
function Invoke-WebRequest {
    param($Uri, $TimeoutSec, [switch]$UseBasicParsing)
    if (-not $script:reuse -and ($script:launched.Count -eq 0 -or ($Uri -notlike '*/version' -and $script:launched.Count -lt 2))) { throw 'not ready' }
    if ($Uri -like '*/version') { return @{StatusCode=200;Content='{"api":"Nexer API","version":"0.1.0"}'} }
    return @{StatusCode=200;Content='<title>Nexer</title><div id="root"></div>'}
}
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, [switch]$PassThru)
    if ($WindowStyle -ne 'Hidden') { throw 'visible console' }
    $script:launched += @{file=$FilePath;args=$ArgumentList;display=$env:NEXER_PAIRING_CODE_DISPLAY}
    return @{HasExited=$false}
}
function Start-Sleep { param($Milliseconds) }
function Get-Command { param($Name, $ErrorAction); return @{Source=$Name} }
$env:NEXER_PAIRING_CODE_DISPLAY = 'console'
. 'LAUNCHER' -NoBrowser -ApiPort 58761 -FrontendPort 58762 -StartupTimeoutSeconds 2
if ($env:NEXER_PAIRING_CODE_DISPLAY -ne 'console') { throw 'environment leaked' }
if ($script:reuse) {
    if ($script:launched.Count -ne 0) { throw 'reused services were restarted' }
} else {
    if ($script:launched.Count -ne 2) { throw 'wrong service count' }
    if ($script:launched[0].display -ne 'window') { throw 'window delivery missing' }
    if ($script:launched[0].args -notlike '*--api-only*') { throw 'queue processing enabled' }
    if ($script:launched[1].args -notlike '*--strictPort*') { throw 'frontend can silently change ports' }
}
Write-Output 'ORCHESTRATION_OK'
'''.replace("REUSE", "$true" if reuse else "$false").replace("LAUNCHER", launcher)
        with tempfile.TemporaryDirectory() as directory:
            # Model installed files without depending on this checkout's node_modules.
            sandbox = Path(directory)
            copied_launcher = sandbox / 'scripts/open_nexer.ps1'
            copied_launcher.parent.mkdir()
            shutil.copyfile(ROOT / 'scripts/open_nexer.ps1', copied_launcher)
            vite = sandbox / 'apps/frontend/node_modules/vite/bin/vite.js'
            vite.parent.mkdir(parents=True)
            vite.touch()
            harness = harness.replace(launcher, str(copied_launcher).replace("'", "''"))
            script = Path(directory) / "harness.ps1"
            script.write_text(harness, encoding="utf-8-sig")
            result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ORCHESTRATION_OK", result.stdout)

    def test_existing_services_are_reused(self):
        self.run_harness(reuse=True)

    def test_missing_services_launch_hidden_with_window_pairing(self):
        self.run_harness(reuse=False)
