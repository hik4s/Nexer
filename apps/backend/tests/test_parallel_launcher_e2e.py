"""Isolated real supervisor, two worker processes and separate Edge sessions."""
import os
import threading
import time
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Automation, AutomationVersion, LoginProfile, LoginProfileVersion, Worker, utcnow
import test_local_launcher_e2e as containment


@unittest.skipUnless(os.name == "nt" and os.getenv("NEXER_RUN_PARALLEL_E2E") == "1", "Isolated two-worker Edge opt-in")
class ParallelLauncherTests(containment.LocalLauncherTests):
    # Inherited containment scenarios already have their own one-worker suite.
    test_launcher_stops_worker_driver_and_edge_gracefully = None
    test_parent_loss_stops_worker_driver_and_edge = None
    test_forced_worker_exit_reaps_owned_driver_and_edge = None
    def setUp(self):
        previous = os.environ.get("NEXER_TEST_WORKERS")
        os.environ["NEXER_TEST_WORKERS"] = "2"
        try: super().setUp()
        finally:
            if previous is None: os.environ.pop("NEXER_TEST_WORKERS", None)
            else: os.environ["NEXER_TEST_WORKERS"] = previous

    def test_parallel_accounts_downloads_and_individual_cancellation(self):
        self.ready()
        engine = create_engine("sqlite:///" + str(self.database))
        self.addCleanup(engine.dispose)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            with Session(engine) as db: workers = db.scalars(select(Worker).where(Worker.status == "ONLINE")).all()
            if len(workers) == 2: break
            time.sleep(.1)
        self.assertEqual(len(workers), 2)
        self.assertNotEqual(workers[0].pid, workers[1].pid)
        entered = {"account-a": threading.Event(), "account-b": threading.Event()}
        release = threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
                account = body.get("user", [""])[0]
                if account not in entered or body.get("pass") != ["synthetic-secret-canary"]:
                    self.send_error(403); return
                self.send_response(303); self.send_header("Set-Cookie", f"account={account}; HttpOnly; SameSite=Strict"); self.send_header("Location", "/home"); self.end_headers()
            def do_GET(self):
                account = self.headers.get("Cookie", "").removeprefix("account=")
                if self.path == "/login": content = b'<form method="post"><input id="user" name="user"><input id="pass" name="pass" type="password"><button id="submit">Enter</button></form>'
                elif account not in entered: self.send_error(403); return
                elif self.path == "/home": content = b'<h1 id="home">Home</h1><a id="download" href="/download" download>Download</a>'
                elif self.path == "/download":
                    entered[account].set()
                    release.wait(25)
                    self.send_response(200); self.send_header("Content-Type", "application/octet-stream"); self.send_header("Content-Disposition", 'attachment; filename="same.txt"'); self.end_headers()
                    try: self.wfile.write(account.encode())
                    except (BrokenPipeError, ConnectionResetError): pass
                    return
                else: self.send_error(404); return
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(content)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown); self.addCleanup(release.set)
        origin = f"http://127.0.0.1:{server.server_port}"
        profile_ids, flows = [], []
        with Session(engine) as db:
            for index in range(2):
                profile = LoginProfile(name=f"Synthetic {index}", status="READY", current_version=1); db.add(profile); db.flush(); profile_ids.append(profile.id)
                configuration = {"login_url": origin + "/login", "allowed_origins": [origin], "username_target": {"selector": "#user", "frames": []}, "password_target": {"selector": "#pass", "frames": []}, "submit_target": {"selector": "#submit", "frames": []}, "success_rule": {"kind": "marker", "target": {"selector": "#home", "frames": []}}}
                db.add(LoginProfileVersion(profile_id=profile.id, version=1, configuration=configuration, published_at=utcnow()))
                automation = Automation(code=f"PARALLEL{index}", name=f"Parallel {index}", status="PUBLISHED", current_version=1); db.add(automation); db.flush(); flows.append(automation.id)
                recipe = {"schema_version": 1, "name": "Parallel", "login_profile": {"id": profile.id, "version": 1}, "variables": {}, "steps": [{"id": "download", "action": "download", "selector": "#download", "filename": "same.txt"}], "output": {"type": "file"}}
                db.add(AutomationVersion(automation_id=automation.id, version=1, recipe=recipe, test_status="PASSED", published_at=utcnow()))
            db.commit()
        payload = {"name": "Parallel synthetic", "idempotency_key": "parallel-isolation-key-001", "items": [{"automation_id": aid, "version": 1, "inputs": {}, "test_mode": False} for aid in flows], "profile_credentials": {f"profile-{pid}-v1": {"username": account, "password": "synthetic-secret-canary"} for pid, account in zip(profile_ids, entered)}}
        response = self.client.post("/execution-batches", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        batch = response.json()
        try:
            self.assertTrue(entered["account-a"].wait(20), "Flow A never reached its real download")
            self.assertTrue(entered["account-b"].wait(20), "Flow B could not overlap the blocked flow A")
            first = batch["executions"][0]["id"]
            self.assertEqual(self.client.post(f"/executions/{first}/cancel").status_code, 200)
        finally: release.set()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = self.client.get(f"/execution-batches/{batch['id']}").json()
            if all(item["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"} for item in result["executions"]): break
            time.sleep(.2)
        self.assertEqual([item["status"] for item in result["executions"]], ["CANCELLED", "SUCCEEDED"], result)
        from pathlib import Path
        downloads = list((Path(self.tmp.name) / "downloads").rglob("same.txt"))
        self.assertTrue(any(path.read_bytes() == b"account-b" for path in downloads))
        import sqlite3
        with closing(sqlite3.connect(self.database)) as db: dump = "\n".join(db.iterdump())
        self.assertNotIn("synthetic-secret-canary", dump)
        # A second batch completes both accounts with the same filename;
        # neither context nor destination directory can overwrite its peer.
        payload["idempotency_key"] = "parallel-isolation-key-002"
        completed = self.client.post("/execution-batches", json=payload)
        self.assertEqual(completed.status_code, 201, completed.text)
        second_id = completed.json()["id"]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            second = self.client.get(f"/execution-batches/{second_id}").json()
            if second["status"] in {"SUCCEEDED", "FAILED", "PARTIAL", "CANCELLED"}: break
            time.sleep(.2)
        self.assertEqual(second["status"], "SUCCEEDED", second)
        files = list((Path(self.tmp.name) / "downloads").rglob("same.txt"))
        account_a = [path for path in files if path.read_bytes() == b"account-a"]
        account_b = [path for path in files if path.read_bytes() == b"account-b"]
        self.assertTrue(account_a and account_b)
        self.assertNotEqual(account_a[0].parent, account_b[0].parent)
        self.stop()
