"""Supervisor contracts without services, browsers, or real pairing output."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from app.config import Settings

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("nexer_local_launcher", ROOT / "scripts/run_local.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class BootstrapPipe:
    def __init__(self):
        self.closed = False
        self.url = None

    def write(self, value):
        self.url = json.loads(value)["url"]

    def flush(self):
        pass

    def close(self):
        self.closed = True


class LocalLauncherTests(unittest.TestCase):
    def run_launcher(self, server):
        worker = Mock()
        worker.stdin = BootstrapPipe()
        worker.poll.return_value = None
        with patch.object(launcher.sys, "argv", ["run_local.py", "--workers", "1"]), \
                patch.object(launcher.os, "chdir"), \
                patch.object(launcher.subprocess, "Popen", return_value=worker) as spawn, \
                patch("app.config.get_settings", return_value=Settings(port=18765)), \
                patch("app.worker_channel.worker_channel.configure") as configure, \
                patch("app.local_pairing.pairing_authority.issue", return_value="synthetic-pairing"), \
                patch("uvicorn.run", side_effect=lambda *args, **kwargs: server(worker, kwargs)), \
                patch("sys.stdout", io.StringIO()) as output:
            launcher.main()
        capability = configure.call_args.args[1]
        self.assertNotIn(capability, json.dumps(spawn.call_args.args))
        self.assertNotIn(capability, json.dumps(spawn.call_args.kwargs["env"]))
        self.assertNotIn(capability, output.getvalue())
        return worker

    def test_configured_port_matches_api_and_worker_transport(self):
        def server(worker, options):
            self.assertEqual(options["port"], 18765)
            self.assertEqual(worker.stdin.url, "http://127.0.0.1:18765")
        self.run_launcher(server)

    def test_parent_keeps_bootstrap_pipe_open_until_server_stops(self):
        def server(worker, options):
            self.assertFalse(worker.stdin.closed)
        worker = self.run_launcher(server)
        self.assertTrue(worker.stdin.closed)
        worker.terminate.assert_not_called()
        worker.wait.assert_called_once()

    def test_two_workers_receive_distinct_private_bootstraps(self):
        workers = [Mock(), Mock()]
        for worker in workers: worker.stdin = io.StringIO(); worker.poll.return_value = None
        observed = []
        def server(*args, **kwargs):
            observed.extend(json.loads(worker.stdin.getvalue()) for worker in workers)
        with patch.object(launcher.sys, "argv", ["run_local.py", "--workers", "2"]), patch.object(launcher.os, "chdir"), patch.object(launcher.subprocess, "Popen", side_effect=workers), patch("app.config.get_settings", return_value=Settings(port=18765)), patch("app.local_pairing.pairing_authority.issue", return_value="synthetic"), patch("uvicorn.run", side_effect=server), patch.object(launcher, "stop_worker"), patch("sys.stdout", io.StringIO()) as output:
            launcher.main()
        self.assertEqual(len(observed), 2)
        self.assertNotEqual(observed[0]["worker_id"], observed[1]["worker_id"])
        self.assertNotEqual(observed[0]["capability"], observed[1]["capability"])
        self.assertNotIn(observed[0]["capability"], output.getvalue())

    def test_worker_observes_parent_pipe_eof_as_stop_request(self):
        import secure_main
        bootstrap = json.dumps({"worker_id": "ephemeral-fixture", "url": "http://127.0.0.1:18765",
                                "capability": "synthetic-fixture-capability"}) + "\n"
        observed = []
        def worker_main(*, worker_id, credential_client, stop_event=None):
            observed.append(stop_event is not None and stop_event.wait(2))
            return 0
        with patch.object(secure_main.sys, "stdin", io.StringIO(bootstrap)), \
                patch.object(secure_main, "main", side_effect=worker_main):
            self.assertEqual(secure_main.entrypoint(), 0)
        self.assertEqual(observed, [True])
