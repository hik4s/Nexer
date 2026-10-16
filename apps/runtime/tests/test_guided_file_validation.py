import hashlib
import tempfile
import unittest
from pathlib import Path

from actions import ActionExecutionError, create_default_registry
from context import ExecutionContext
from recipe import RecipeValidationError, validate_recipe
from runner import RecipeRunner


def recipe(*steps):
    return {"schema_version": 1, "name": "Local download", "variables": {},
            "steps": list(steps), "output": {"type": "file"}}


class _Download:
    suggested_filename = "actual-from-browser.csv"

    def save_as(self, path):
        Path(path).write_bytes(b"header,value\nA,42\n")


class _Expectation:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    @property
    def value(self):
        return _Download()


class _Locator:
    def click(self, **_kwargs):
        return None


class _Page:
    def expect_download(self, **_kwargs):
        return _Expectation()

    def locator(self, _selector):
        return _Locator()


DOWNLOAD = {"id": "fetch", "action": "download", "selector": "#export",
            "filename": "fallback", "preserve_filename": True}
VALIDATE = {"id": "verify", "action": "validate_file",
            "source_download": "fetch", "min_size": 1}


class GuidedFileValidationTests(unittest.TestCase):
    def test_reference_must_point_to_previous_download_and_has_no_path_fallback(self):
        for steps in [
            [VALIDATE, DOWNLOAD],
            [{"id": "click", "action": "click", "selector": "#export"}, {**VALIDATE, "source_download": "click"}],
            [DOWNLOAD, {**VALIDATE, "source_download": "missing"}],
            [DOWNLOAD, {**VALIDATE, "path": "stale.csv"}],
        ]:
            with self.subTest(steps=steps):
                with self.assertRaisesRegex(RecipeValidationError, "FILE_VALIDATION_SOURCE_INVALID"):
                    validate_recipe(recipe(*steps))
        with self.assertRaisesRegex(RecipeValidationError, "FILE_VALIDATION_SOURCE_INVALID"):
            validate_recipe(recipe(DOWNLOAD, {"id": "verify", "action": "validate_file"}))

    def test_preserved_site_filename_is_validated_without_guessing(self):
        with tempfile.TemporaryDirectory() as path:
            context = ExecutionContext(page=_Page(), variables={}, downloads_dir=Path(path))
            result = RecipeRunner().run(recipe(DOWNLOAD, VALIDATE), context)
            self.assertIsNone(result.failed_step_id, result.error)
            self.assertEqual(result.completed_steps, 2)
            validation = [x for x in context.artifacts if x["type"] == "validated_file"]
            self.assertEqual(len(validation), 1)
            self.assertEqual(Path(validation[0]["path"]).name, "actual-from-browser.csv")
            self.assertEqual(validation[0]["checksum"], hashlib.sha256(b"header,value\nA,42\n").hexdigest())
            self.assertEqual(context.download_outputs, {})

    def test_source_cannot_be_reused_from_previous_execution(self):
        with tempfile.TemporaryDirectory() as path:
            context = ExecutionContext(page=_Page(), variables={}, downloads_dir=Path(path))
            context.download_outputs["fetch"] = Path(path) / "existing.csv"
            (Path(path) / "existing.csv").write_bytes(b"wrong")
            # Lookup is isolated to the current run. A syntactically valid recipe can never
            # validate a file from a previous context or from a user-supplied path.
            context.download_outputs.clear()
            with self.assertRaisesRegex(ActionExecutionError, "DOWNLOAD_SOURCE_UNAVAILABLE"):
                create_default_registry().execute("validate_file", VALIDATE, context)


if __name__ == "__main__":
    unittest.main()
