"""Guards for portable Windows distribution; no corporate access or app startup."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortableDistributionTests(unittest.TestCase):
    def test_required_sources_and_lockfiles_exist(self):
        required = (
            ".gitignore", ".env.example", "data/.gitkeep",
            "Instalar-Nexer.cmd", "Abrir-Nexer.cmd",
            "scripts/install_nexer.ps1",
            "scripts/requirements-windows-py312.lock.txt",
            "apps/frontend/package-lock.json",
            "apps/backend/alembic.ini",
            "apps/backend/alembic/versions/0007_practical_workspace.py",
            "apps/worker/requirements.txt",
        )
        for name in required:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file(), name)

    def test_credentials_example_does_not_ask_for_corporate_password(self):
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertNotIn("SITE_SENHA=", template)
        self.assertNotIn("SITE_USUARIO=", template)
        self.assertIn("NEXER_PORT=", template)

    def test_git_ignore_protects_runtime_but_not_distribution(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        ignored = ("data/nexer.db", ".env", ".env.local", "apps/frontend/node_modules/index.js",
                   ".venv/Scripts/python.exe", "downloads/report.csv", "logs/worker.log")
        essential = (".env.example", "data/.gitkeep", "Instalar-Nexer.cmd",
                     "scripts/requirements-windows-py312.lock.txt",
                     "apps/frontend/package-lock.json",
                     "apps/backend/alembic.ini",
                     "apps/backend/alembic/versions/0007_practical_workspace.py")
        for name in ignored + essential:
            with self.subTest(name=name):
                result = subprocess.run(
                    ["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", "--", name],
                    capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 0 if name in ignored else 1, name)

    def test_no_database_is_tracked_in_git(self):
        if shutil.which("git") is None or not (ROOT / ".git").exists():
            self.skipTest("No .git checkout")
        result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", "data/nexer.db"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_installer_preserves_safe_api_only_mode(self):
        installer = (ROOT / "scripts/install_nexer.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "scripts/open_nexer.ps1").read_text(encoding="utf-8")
        self.assertIn("-NoLaunch", (ROOT / "docs/INSTALACAO_DO_GITHUB.md").read_text(encoding="utf-8"))
        self.assertIn("UpgradeExistingDatabase", installer)
        self.assertIn("run_local.py", launcher)
        self.assertIn("--api-only", launcher)


if __name__ == "__main__":
    unittest.main()
