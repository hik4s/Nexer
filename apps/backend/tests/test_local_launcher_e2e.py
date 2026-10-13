"""Opt-in Windows launcher tests with an empty temporary queue and actual Edge."""
from contextlib import closing
import ctypes
import json
import os
from pathlib import Path
import queue
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import httpx

HELPER = Path(__file__).with_name("local_launcher_fixture.py")


def process_rows():
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=15, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    return json.loads(result.stdout)


def descendants(root, rows):
    owned = {root}
    while True:
        found = {row["ProcessId"] for row in rows if row["ParentProcessId"] in owned}
        if found <= owned:
            return owned - {root}
        owned |= found


def running(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE only.
    if not handle:
        if ctypes.get_last_error() == 87:  # No such process.
            return False
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return kernel.WaitForSingleObject(handle, 0) == 258
    finally:
        kernel.CloseHandle(handle)


@unittest.skipUnless(os.name == "nt" and os.getenv("NEXER_RUN_LAUNCHER_E2E") == "1",
                     "Set NEXER_RUN_LAUNCHER_E2E=1 for isolated Windows launcher/Edge tests")
class LocalLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "launcher.db"
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            self.port = port_socket.getsockname()[1]
        environment = os.environ.copy()
        environment.update(NEXER_DATABASE_URL=f"sqlite:///{self.database}",
            NEXER_PORT=str(self.port), NEXER_DOWNLOADS_ROOT=str(Path(self.tmp.name) / "downloads"),
            PYTHONDONTWRITEBYTECODE="1")
        self.process = subprocess.Popen([sys.executable, str(HELPER)], cwd=self.tmp.name,
            env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.owned = set()
        self.lines = []
        self.codes = queue.Queue()
        def read():
            for line in self.process.stdout:
                if line.startswith("Código de pareamento"):
                    self.codes.put(line.rsplit(":", 1)[1].strip())
                else:
                    self.lines.append(line)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        self.addCleanup(self.stop)
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.port}",
            headers={"Origin": "http://127.0.0.1:5173"}, trust_env=False, timeout=2)
        self.addCleanup(self.client.close)

    def stop(self):
        if self.process.poll() is None:
            self.owned |= descendants(self.process.pid, process_rows())
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            try:
                self.process.wait(timeout=100)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process.stdin.close()
        self.reader.join(timeout=5)
        self.process.stdout.close()
        # Cleanup only PIDs observed in this isolated subprocess tree.
        for pid in self.owned:
            if running(pid):
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)

    def ready(self):
        code = self.codes.get(timeout=20)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if self.client.get("/health").status_code == 200:
                    with closing(sqlite3.connect(self.database)) as connection:
                        row = connection.execute("SELECT pid FROM workers WHERE status='ONLINE'").fetchone()
                    if row:
                        self.worker_pid = row[0]
                        break
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        else:
            self.fail("Isolated launcher/API/worker failed to become ready")
        self.assertEqual(self.client.post("/auth/login", json={"pairing_code": code}).status_code, 200)
        code = None
        self.assertEqual(self.client.get("/auth/session").status_code, 200)
        rows = process_rows()
        self.owned = descendants(self.process.pid, rows)
        self.assertIn(self.worker_pid, self.owned)
        self.assertTrue(any(row["ProcessId"] in self.owned and row["Name"].lower() == "msedge.exe"
                            for row in rows), "Real idle worker must own an Edge process")
        response = self.client.post("/executions", json={"name": "Gate fixture", "automation_ids": [1],
            "corporate_credentials": {"SGIND": {"username": "synthetic-user", "password": "synthetic-password"}}}
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "CORPORATE_AUTH_NOT_VALIDATED")
        self.assertNotIn("synthetic-password", response.text)

    def scenario(self, command):
        self.ready()
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        self.process.wait(timeout=100)
        self.assertEqual(self.process.returncode, 23 if command == "crash" else 0)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and any(running(pid) for pid in self.owned):
            time.sleep(0.05)
        self.assertFalse(any(running(pid) for pid in self.owned), "Owned worker/driver/Edge processes survived")
        with closing(sqlite3.connect(self.database)) as connection:
            worker = connection.execute("SELECT status, stopped_at FROM workers WHERE pid=?", (self.worker_pid,)).fetchone()
            count = connection.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
            dump = "\n".join(connection.iterdump())
        if command == "kill-worker":
            self.assertEqual(worker[0], "ONLINE")  # Forced exit cannot claim graceful cleanup.
            self.assertIsNone(worker[1])
        else:
            self.assertEqual(worker[0], "OFFLINE")
            self.assertIsNotNone(worker[1])
        self.assertEqual(count, 0)
        self.assertNotIn("synthetic-password", dump)
        self.reader.join(timeout=5)
        self.assertFalse(self.reader.is_alive())
        self.assertNotIn("Traceback", "".join(self.lines))

    def test_launcher_stops_worker_driver_and_edge_gracefully(self):
        self.scenario("stop")

    def test_parent_loss_stops_worker_driver_and_edge(self):
        self.scenario("crash")

    def test_forced_worker_exit_reaps_owned_driver_and_edge(self):
        self.scenario("kill-worker")


@unittest.skipUnless(os.name == "nt" and os.getenv("NEXER_RUN_LAUNCHER_E2E") == "1",
                     "Set NEXER_RUN_LAUNCHER_E2E=1 for isolated Windows process containment")
class WorkerContainmentTests(unittest.TestCase):
    def test_supervisor_timeout_terminates_child_ignoring_shutdown(self):
        helper = Path(__file__).with_name("worker_containment_fixture.py")
        process = subprocess.Popen([sys.executable, str(helper)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        child_pid = None
        try:
            process.stdin.write(json.dumps({"worker_id": "ephemeral-contained-fixture",
                "url": "http://127.0.0.1:18765", "capability": "synthetic-containment-capability"}) + "\n")
            process.stdin.flush()
            messages = queue.Queue()
            reader = threading.Thread(target=lambda: messages.put(process.stdout.readline()), daemon=True)
            reader.start()
            message = json.loads(messages.get(timeout=15))
            child_pid = message["child_pid"]
            self.assertTrue(running(child_pid))
            import importlib.util
            spec = importlib.util.spec_from_file_location("launcher_timeout_fixture",
                HELPER.parents[3] / "scripts/run_local.py")
            launcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(launcher)
            launcher.stop_worker(process, timeout=0.2)
            deadline = time.monotonic() + 5
            while running(child_pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertFalse(running(child_pid), "Blocked child escaped supervisor timeout shutdown")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if child_pid is not None and running(child_pid):
                subprocess.run(["taskkill", "/PID", str(child_pid), "/T", "/F"],
                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            process.stdin.close()
            process.stdout.close()
