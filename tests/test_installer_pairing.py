"""Execute the installer in a temporary tree with external commands intercepted.

No dependencies, migrations, credentials or services are actually created.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "Windows installer")
class InstallerPairingTests(unittest.TestCase):
    def run_installer(self, *options, existing_database=False, include_legacy=False):
        with tempfile.TemporaryDirectory(prefix="nexer-installer-") as directory:
            root = Path(directory)
            paths = [
                "scripts/install_nexer.ps1", "scripts/run_local.py",
                "scripts/open_nexer.ps1", "apps/worker/requirements.txt",
                "apps/frontend/package.json", "apps/frontend/package-lock.json",
                "apps/backend/alembic.ini", "apps/backend/alembic/env.py",
                "scripts/requirements-windows-py312.lock.txt",
                ".venv/Scripts/python.exe",
            ]
            if include_legacy:
                paths.append("scripts/setup_auth.py")
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            shutil.copyfile(ROOT / "scripts/install_nexer.ps1", root / paths[0])
            (root / "scripts/open_nexer.ps1").write_text(
                "Add-Content -LiteralPath $env:NEXER_TEST_CALLS -Value 'LAUNCH'", encoding="utf-8")
            if existing_database:
                (root / "data").mkdir()
                (root / "data/nexer.db").write_bytes(b"preserve-me")
            harness = root / "harness.ps1"
            harness.write_text(r'''
param([string[]]$InstallerOptions)
$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'scripts/install_nexer.ps1'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($installer, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Installer parse error' }
# Replace only the external process boundary; execute all installer control flow.
$boundary = $ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-Checked'}, $true)
$replacement = @'
function Invoke-Checked([string]$program, [string[]]$arguments) {
    Add-Content -LiteralPath $env:NEXER_TEST_CALLS -Value ($arguments -join ' ')
    if (($arguments -join ' ') -match 'setup_auth.py') { throw 'LEGACY_PASSWORD_PROMPT' }
}
'@
$source = [IO.File]::ReadAllText($installer)
$source = $source.Remove($boundary.Extent.StartOffset, $boundary.Extent.EndOffset - $boundary.Extent.StartOffset).Insert($boundary.Extent.StartOffset, $replacement)
[IO.File]::WriteAllText($installer, $source)
function Get-Command { param($Name, $ErrorAction) [pscustomobject]@{Source=$Name} }
function node.exe { $global:LASTEXITCODE = 0; 'v24.0.0' }
function Get-NetTCPConnection { param($LocalPort, $State, $ErrorAction) }
& $installer @InstallerOptions
''', encoding="utf-8")
            env = os.environ.copy()
            for name in ("NEXER_DATABASE_URL", "NEXER_ENVIRONMENT"):
                env.pop(name, None)
            calls = root / "calls.txt"
            env["NEXER_TEST_CALLS"] = str(calls)
            # Pass switches directly through a wrapper expression to retain switch binding.
            invocation = "& '" + str(harness).replace("'", "''") + "' -InstallerOptions @(" + ",".join("'" + x + "'" for x in options) + ")"
            # InstallerOptions must be splatted as named switches, not positional strings.
            content = harness.read_text(encoding="utf-8").replace(
                "& $installer @InstallerOptions", "$switches = @{}; foreach ($option in $InstallerOptions) { $switches[$option.TrimStart('-')] = $true }; & $installer @switches")
            harness.write_text(content, encoding="utf-8")
            result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", invocation],
                                    env=env, capture_output=True, text=True, timeout=30)
            recorded = calls.read_text(encoding="utf-8-sig") if calls.exists() else ""
            database = (root / "data/nexer.db").read_bytes() if existing_database else None
            return result, recorded, database

    def test_clean_install_needs_no_legacy_auth_script(self):
        result, calls, _ = self.run_installer("-NoLaunch")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("upgrade head", calls)
        self.assertNotIn("LAUNCH", calls)

    def test_install_does_not_prompt_for_legacy_password(self):
        result, calls, _ = self.run_installer("-NoLaunch", include_legacy=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("setup_auth.py", calls)

    def test_legacy_skip_option_keeps_its_no_launch_safety(self):
        result, calls, _ = self.run_installer("-SkipAuthSetup", include_legacy=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("LAUNCH", calls)

    def test_normal_install_reaches_launcher_without_password(self):
        result, calls, _ = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LAUNCH", calls)

    def test_existing_database_is_preserved_before_external_commands(self):
        result, calls, database = self.run_installer("-NoLaunch", existing_database=True, include_legacy=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(database, b"preserve-me")
        self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()
