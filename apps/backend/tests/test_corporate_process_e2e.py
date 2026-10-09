"""Opt-in actual API and worker subprocesses, isolated DB and synthetic Edge pages."""
import json
import os
from pathlib import Path
import queue
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import httpx


ROOT = Path(__file__).resolve().parents[3]
HELPER = Path(__file__).with_name("corporate_process_fixture.py")
CANARY = "synthetic-process-password-942"


@unittest.skipUnless(os.getenv("NEXER_RUN_CORPORATE_PROCESS_E2E") == "1",
                     "Set NEXER_RUN_CORPORATE_PROCESS_E2E=1 for isolated process fixtures")
class CorporateProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.database = self.directory / "fixture.db"
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            self.port = port_socket.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.processes = []
        self.captured = []
        self.readers = []
        self.addCleanup(self.stop_processes)
        self.configuration = {"port": self.port, "worker_id": "synthetic-process-worker",
                              "capability": "synthetic-process-capability", "url": self.url}

    def stop_processes(self):
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        for reader in self.readers:
            reader.join(timeout=2)
        for process in self.processes:
            if process.stdout:
                process.stdout.close()

    def spawn(self, mode):
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["NEXER_DATABASE_URL"] = f"sqlite:///{self.database}"
        environment["NEXER_PORT"] = str(self.port)
        process = subprocess.Popen([sys.executable, str(HELPER), mode],
            cwd=self.directory, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.processes.append(process)
        process.stdin.write(json.dumps(self.configuration) + "\n")
        process.stdin.close()
        messages = queue.Queue()
        def read():
            for line in process.stdout:
                self.captured.append(line)
                try:
                    messages.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        reader = threading.Thread(target=read, daemon=True)
        self.readers.append(reader)
        reader.start()
        return process, messages

    def wait_message(self, messages, key):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=0.2)
                if key in message:
                    return message
            except queue.Empty:
                pass
        self.fail("Subprocess did not produce the expected lifecycle message")

    def start_api(self):
        process, messages = self.spawn("api")
        code = self.wait_message(messages, "ready")["pairing_code"]
        client = httpx.Client(base_url=self.url, trust_env=False, timeout=2,
                             headers={"Origin": "http://127.0.0.1:5173"})
        self.addCleanup(client.close)
        deadline = time.monotonic() + 10
        while True:
            try:
                if client.get("/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                self.fail("Fixture API did not listen")
            time.sleep(0.05)
        response = client.post("/auth/login", json={"pairing_code": code})
        self.assertEqual(response.status_code, 200)
        return process, client

    def wait_until_action(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with sqlite3.connect(self.database) as connection:
                count = connection.execute("SELECT COUNT(*) FROM events WHERE type='action.started'").fetchone()[0]
            if count:
                return
            time.sleep(0.05)
        self.fail("Worker did not reach the pending browser action")

    def run_scenario(self, scenario):
        self.configuration["scenario"] = scenario
        api, client = self.start_api()
        worker, messages = self.spawn("worker")
        self.wait_message(messages, "worker_ready")
        response = client.post("/executions", json={
            "name": "Synthetic process execution", "automation_ids": [1],
            "corporate_credentials": {"SGIND": {"username": "synthetic-process-user",
                                               "password": CANARY}}})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn(CANARY, response.text)
        execution_id = response.json()["id"]
        if scenario != "success":
            self.wait_until_action()
            if scenario == "cancel":
                self.assertEqual(client.post(f"/executions/{execution_id}/cancel").status_code, 200)
            elif scenario == "logout":
                self.assertEqual(client.post("/auth/logout").status_code, 200)
            elif scenario == "restart":
                api.terminate()
                api.wait(timeout=5)
                _, client = self.start_api()
        result = self.wait_message(messages, "status")
        worker.wait(timeout=10)
        self.assertEqual(worker.returncode, 0)
        expected = "SUCCEEDED" if scenario == "success" else ("CANCELLED" if scenario == "cancel" else "FAILED")
        self.assertEqual(result["status"], expected)
        with sqlite3.connect(self.database) as connection:
            dump = "\n".join(connection.iterdump())
            item = connection.execute("SELECT status FROM execution_automations").fetchone()[0]
        self.assertEqual(item, expected)
        self.assertNotIn(CANARY, dump)
        self.assertNotIn(self.configuration["capability"], dump)
        self.assertNotIn(CANARY, "".join(self.captured))
        self.assertNotIn(self.configuration["capability"], "".join(self.captured))
        capability_headers = {"x-nexer-worker": self.configuration["capability"]}
        response = client.get(f"/internal/credentials/{execution_id}/SGIND", headers=capability_headers)
        self.assertGreaterEqual(response.status_code, 400)
        self.assertNotIn(CANARY, response.text)
        if scenario == "success":
            report = self.directory / "downloads" / str(execution_id) / "1" / "report.txt"
            self.assertEqual(report.read_bytes(), b"synthetic-report")

    def test_success_download_and_cleanup_between_real_processes(self):
        self.run_scenario("success")

    def test_cancel_interrupts_pending_browser_and_cleans_credentials(self):
        self.run_scenario("cancel")

    def test_logout_interrupts_pending_browser_and_cleans_credentials(self):
        self.run_scenario("logout")

    def test_api_restart_invalidates_worker_credentials(self):
        self.run_scenario("restart")
