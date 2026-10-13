from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ProjectSmokeTests(unittest.TestCase):
    def test_required_entrypoints_exist(self):
        required = [
            "launcher.py",
            "worker.py",
            "auth.py",
            "config.py",
            "main.py",
            "Requisitos.txt",
        ]
        for name in required:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file(), name)

    def test_expected_runtime_directories_exist(self):
        for name in ("core", "relatorios", "ui", "assets"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_dir(), name)

    def test_local_credentials_file_is_not_present_in_repository_checkout(self):
        self.assertFalse((ROOT / ".env").exists())

    def test_requirements_file_is_non_empty(self):
        requirements = (ROOT / "Requisitos.txt").read_text(encoding="utf-8")
        self.assertTrue(requirements.strip())
        self.assertIn("playwright", requirements.lower())
        self.assertIn("streamlit", requirements.lower())

if __name__ == "__main__":
    unittest.main()
