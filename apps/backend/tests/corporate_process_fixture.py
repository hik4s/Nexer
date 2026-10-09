"""Test-only subprocess entry points. Never used by the production launcher."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
for folder in ("apps/backend", "apps/worker", "apps/runtime", "apps/runtime/tests"):
    sys.path.insert(0, str(ROOT / folder))


def api(configuration):
    import uvicorn
    from app.database import engine, SessionLocal
    from app.models import Base, Automation, AutomationVersion
    from app.main import app
    from app.api.executions import require_validated_corporate_auth
    from app.local_pairing import pairing_authority
    from app.worker_channel import worker_channel
    from sqlalchemy import select
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(Automation)) is None:
            automation = Automation(code="PROCESS_FIXTURE", name="Process fixture",
                system="SGIND", status="PUBLISHED", current_version=1)
            db.add(automation)
            db.flush()
            step = ({"id": "download", "action": "download", "selector": "#download",
                     "filename": "report.txt", "timeout_ms": 5000}
                    if configuration["scenario"] == "success" else
                    {"id": "pending", "action": "wait_for", "selector": "#never",
                     "timeout_ms": 30000})
            db.add(AutomationVersion(automation_id=automation.id, version=1,
                recipe={"schema_version": 1, "name": "Process fixture", "variables": {},
                        "steps": [step], "output": {"type": "file"}},
                test_status="PASSED"))
            db.commit()
    # Synthetic approval only in this test entry point, not environment or request.
    app.dependency_overrides[require_validated_corporate_auth] = lambda: None
    worker_channel.configure(configuration["worker_id"], configuration["capability"])
    print(json.dumps({"ready": True, "pairing_code": pairing_authority.issue()}), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=configuration["port"], access_log=False,
                proxy_headers=False, log_level="critical")


def worker(configuration):
    import threading
    from http.server import ThreadingHTTPServer
    from unittest.mock import patch
    from app.database import SessionLocal
    from nexer_worker.service import WorkerService
    from nexer_worker.processor import WorkerExecutionProcessor
    from nexer_worker.credential_client import ExecutionCredentialClient
    from monitored_browser import MonitoredCorporatePage
    from test_monitored_edge import AsyncFixturePlaywright, MonitoredHandler
    server = ThreadingHTTPServer(("127.0.0.1", 0), MonitoredHandler)
    server.started = threading.Event()
    server.release = threading.Event()
    server.release.set()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    service = WorkerService(session_factory=SessionLocal,
        worker_id=configuration["worker_id"], pid=os.getpid())
    service.register()
    client = ExecutionCredentialClient(configuration["url"], configuration["capability"])
    def factory(system, authorize):
        fixture = AsyncFixturePlaywright(f"http://127.0.0.1:{server.server_port}")
        return MonitoredCorporatePage(system, authorize=authorize,
            playwright_factory=lambda: fixture, poll_seconds=0.05)
    def unrestricted(*args):
        raise RuntimeError("UNRESTRICTED_BROWSER_FORBIDDEN")
    processor = WorkerExecutionProcessor(session_factory=SessionLocal, worker_service=service,
        page_factory=unrestricted, corporate_page_factory=factory,
        credential_client=client, downloads_root=Path.cwd() / "downloads")
    print(json.dumps({"worker_ready": True}), flush=True)
    try:
        with patch("nexer_worker.processor.require_validated_adapter"):
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                service.heartbeat()
                result = processor.process_once()
                if result.execution_id is not None:
                    print(json.dumps({"status": result.status}), flush=True)
                    return
                time.sleep(0.05)
            raise RuntimeError("FIXTURE_EXECUTION_TIMEOUT")
    finally:
        service.stop()
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    bootstrap = json.loads(sys.stdin.readline(4096))
    if sys.argv[1] == "api":
        api(bootstrap)
    elif sys.argv[1] == "worker":
        worker(bootstrap)
