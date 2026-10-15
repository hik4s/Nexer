import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Base, Automation, Execution, ExecutionAutomation, Artifact
from app.config import get_settings, Settings
from app.security import SESSION_COOKIE_NAME, issue_session


class ExecutionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'downloads'
        self.engine = create_engine('sqlite:///' + str(Path(self.tmp.name) / 'test.db'))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine)
        with self.sessions() as db:
            automation = Automation(code='fixture', name='Fixture')
            execution = Execution(name='One', status='SUCCEEDED')
            other = Execution(name='Two', status='SUCCEEDED')
            db.add_all([automation, execution, other]); db.flush()
            item = ExecutionAutomation(execution_id=execution.id, automation_id=automation.id,
                                       automation_version=1, status='SUCCEEDED')
            db.add(item); db.flush()
            self.execution_id, self.other_id, self.item_id = execution.id, other.id, item.id
            self.path = self.root / str(execution.id) / str(item.id) / 'result.csv'
            self.path.parent.mkdir(parents=True)
            self.content = b'company,total\nA,42\n'
            self.path.write_bytes(self.content)
            row = Artifact(execution_automation_id=item.id, type='VALIDATED_FILE',
                           filename='result.csv', local_path=str(self.path), size=len(self.content),
                           checksum=hashlib.sha256(self.content).hexdigest())
            db.add(row); db.commit(); self.artifact_id = row.id
        def database():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_settings] = lambda: Settings(downloads_root=str(self.root))
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 50000))
        self.addCleanup(self.client.close)
        self.client.cookies.set(SESSION_COOKIE_NAME, issue_session('test', 600))

    def url(self, execution=None):
        return f'/executions/{execution or self.execution_id}/artifacts'

    def test_list_and_authenticated_download_expose_no_local_paths(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'][0]['filename'], 'result.csv')
        self.assertNotIn('local_path', response.text)
        self.assertNotIn(str(self.root), response.text)
        download = self.client.get(f'{self.url()}/{self.artifact_id}/download')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, self.content)
        self.assertEqual(download.headers['cache-control'], 'no-store')
        self.assertEqual(download.headers['x-content-type-options'], 'nosniff')
        self.assertIn('attachment', download.headers['content-disposition'])

    def test_other_execution_and_missing_session_cannot_download(self):
        self.assertEqual(self.client.get(f'{self.url(self.other_id)}/{self.artifact_id}/download').status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.url()).status_code, 401)
        self.assertEqual(self.client.get(f'{self.url()}/{self.artifact_id}/download').status_code, 401)

    def test_changed_missing_and_unsafe_paths_fail_closed(self):
        url = f'{self.url()}/{self.artifact_id}/download'
        self.path.write_bytes(b'company,total\nB,99\n')
        self.assertEqual(self.client.get(url).status_code, 409)
        self.path.unlink()
        self.assertEqual(self.client.get(url).status_code, 409)
        for filename in ('../outside.csv', 'result.csv:secret', 'C:\\secret.csv'):
            with self.sessions() as db:
                row = db.get(Artifact, self.artifact_id); row.filename = filename; db.commit()
            self.assertEqual(self.client.get(url).status_code, 409)

    def test_only_successful_items_expose_validated_files(self):
        with self.sessions() as db:
            db.get(ExecutionAutomation, self.item_id).status = 'FAILED'; db.commit()
        self.assertEqual(self.client.get(self.url()).json(), {'items': []})
        self.assertEqual(self.client.get(f'{self.url()}/{self.artifact_id}/download').status_code, 404)

    def test_hardlinked_file_is_not_served(self):
        outside = Path(self.tmp.name) / 'outside.csv'
        self.path.rename(outside)
        os.link(outside, self.path)
        self.assertEqual(self.client.get(f'{self.url()}/{self.artifact_id}/download').status_code, 409)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction containment')
    def test_junction_to_another_directory_is_not_served(self):
        import subprocess
        target = Path(self.tmp.name) / 'outside'
        self.path.parent.rename(target)
        environment = os.environ.copy()
        environment.update(NEXER_TEST_LINK=str(self.path.parent), NEXER_TEST_TARGET=str(target))
        result = subprocess.run(['powershell','-NoProfile','-Command',
            'New-Item -ItemType Junction -Path $env:NEXER_TEST_LINK -Target $env:NEXER_TEST_TARGET | Out-Null'],
            env=environment, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        try:
            self.assertEqual(self.client.get(f'{self.url()}/{self.artifact_id}/download').status_code, 409)
        finally:
            os.rmdir(self.path.parent)


class ArtifactCollectionTests(unittest.TestCase):
    def test_downloading_again_after_validation_requires_a_new_validation(self):
        from app.services.execution_artifacts import collect_artifacts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / '7' / '9' / 'result.csv'
            path.parent.mkdir(parents=True); path.write_bytes(b'A,42\n')
            with self.assertRaisesRegex(RuntimeError, 'ARTIFACT_NOT_VALIDATED'):
                collect_artifacts([{'type':'validated_file','path':str(path),'size':5},
                                   {'type':'download','path':str(path)}], root, 7, 9)

    def test_file_changed_to_same_size_after_runtime_validation_is_rejected(self):
        from app.services.execution_artifacts import collect_artifacts
        from actions import create_default_registry
        from context import ExecutionContext
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / '7' / '9' / 'result.csv'
            context = ExecutionContext(page=None,variables={},downloads_dir=path.parent)
            path.write_bytes(b'A,42\n')
            create_default_registry().execute('validate_file',{'id':'validate','path':str(path)},context)
            path.write_bytes(b'B,99\n')
            with self.assertRaisesRegex(RuntimeError, 'ARTIFACT_UNAVAILABLE'):
                collect_artifacts(context.artifacts, root, 7, 9)

    def test_parent_segments_in_configured_root_match_runtime_resolved_paths(self):
        from app.services.execution_artifacts import collect_artifacts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'nested').mkdir()
            configured = root / 'nested' / '..'
            path = root / '7' / '9' / 'result.csv'
            path.parent.mkdir(parents=True); path.write_bytes(b'A,42\n')
            rows = collect_artifacts([{'type':'download','path':str(configured / '7' / '9' / 'result.csv')},
                {'type':'validated_file','path':str(path.resolve()),'size':5}], configured, 7, 9)
            self.assertEqual(len(rows),1)

    def test_validated_file_is_hashed_and_deduplicated(self):
        from app.services.execution_artifacts import collect_artifacts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / '7' / '9' / 'result.csv'
            path.parent.mkdir(parents=True); path.write_bytes(b'A,42\n')
            validated = {'type': 'validated_file', 'path': str(path), 'size': 5}
            rows = collect_artifacts([{'type': 'download', 'path': str(path)}, validated, validated], root, 7, 9)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['checksum'], hashlib.sha256(b'A,42\n').hexdigest())

    def test_unvalidated_changed_and_other_job_files_are_rejected(self):
        from app.services.execution_artifacts import collect_artifacts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / '7' / '9' / 'result.csv'
            path.parent.mkdir(parents=True); path.write_bytes(b'A,42\n')
            for entries, execution in [
                ([{'type':'download','path':str(path)}], 7),
                ([{'type':'validated_file','path':str(path),'size':99}], 7),
                ([{'type':'validated_file','path':str(path),'size':5}], 8),
            ]:
                with self.assertRaises(RuntimeError): collect_artifacts(entries, root, execution, 9)


if __name__ == '__main__':
    unittest.main()
