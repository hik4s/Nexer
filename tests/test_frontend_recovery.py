"""One-time frontend recovery: no network, API, database, worker or production process."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def powershell(*arguments):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", *map(str, arguments)],
        capture_output=True, text=True, timeout=20,
    )


class FrontendRecoveryTests(unittest.TestCase):
    def test_launch_refuses_missing_frontend_without_starting_any_service(self):
        with tempfile.TemporaryDirectory(prefix="nexer-preflight-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/open_nexer.ps1", root / "scripts/open_nexer.ps1")
            # Neither frontend packages nor the API have been provisioned.
            result = powershell("-File", root / "scripts/open_nexer.ps1",
                                "-NoBrowser", "-ApiPort", "58761", "-FrontendPort", "58762")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Preparar-Frontend-Nexer.cmd", result.stderr + result.stdout)
            self.assertIn("A API nao foi reiniciada", result.stderr + result.stdout)

    def test_restart_refuses_missing_frontend_before_touching_existing_api(self):
        with tempfile.TemporaryDirectory(prefix="nexer-restart-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/manage_nexer.ps1", root / "scripts/manage_nexer.ps1")
            result = powershell("-File", root / "scripts/manage_nexer.ps1", "-Action", "restart")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Preparar-Frontend-Nexer.cmd", result.stderr + result.stdout)
            self.assertIn("API existente nao foi interrompida", result.stderr + result.stdout)

    def test_preparation_is_idempotent_when_frontend_already_installed(self):
        with tempfile.TemporaryDirectory(prefix="nexer-frontend-ready-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/prepare_frontend.ps1", root / "scripts/prepare_frontend.ps1")
            frontend = root / "apps/frontend"
            frontend.mkdir(parents=True)
            (frontend / "package.json").write_text('{"name":"nexer"}', encoding="utf-8")
            (frontend / "package-lock.json").write_text('{"lockfileVersion":3}', encoding="utf-8")
            vite = frontend / "node_modules/vite/bin/vite.js"
            vite.parent.mkdir(parents=True)
            vite.write_text("ready", encoding="utf-8")
            result = powershell("-File", root / "scripts/prepare_frontend.ps1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ja preparada", result.stdout)
            self.assertEqual(vite.read_text(encoding="utf-8"), "ready")
            self.assertFalse((root / "data/nexer.db").exists())

    def test_recovery_scripts_exist_and_do_not_target_user_data(self):
        self.assertTrue((ROOT / "Preparar-Frontend-Nexer.cmd").is_file())
        setup = (ROOT / "scripts/prepare_frontend.ps1").read_text(encoding="utf-8")
        self.assertIn("ci --prefix", setup)
        self.assertNotIn("migrate", setup.lower())
        self.assertNotIn("setup_auth", setup.lower())
        self.assertNotIn("Stop-Process", setup)


if __name__ == "__main__":
    unittest.main()
