"""Executable entry point for the Nexer Worker."""

import os
import signal
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from app.database import SessionLocal
from browser_manager import BrowserManager
from nexer_worker.loop import WorkerLoop
from nexer_worker.processor import WorkerExecutionProcessor
from nexer_worker.service import WorkerService


@dataclass
class WorkerApp:
    loop: WorkerLoop
    browser_manager: BrowserManager


def build_worker(*, browser_manager: BrowserManager | None = None, worker_id=None, credential_client=None) -> WorkerApp:
    worker_id = worker_id or os.getenv("NEXER_WORKER_ID") or f"worker-{os.getpid()}"
    concurrency = int(os.getenv("NEXER_WORKER_CONCURRENCY", "1"))
    downloads_root = Path(
        os.getenv("NEXER_DOWNLOADS_ROOT", "./downloads")
    )
    headless = _env_bool("NEXER_BROWSER_HEADLESS", default=True)

    manager = browser_manager or BrowserManager(
        headless=headless,
        temp_root=downloads_root,
    )
    manager.start()

    def page_factory(execution, item, recipe):
        return manager.create_page(f"{execution.id}-{item.id}")

    service = WorkerService(
        session_factory=SessionLocal,
        worker_id=worker_id,
        concurrency_limit=concurrency,
        pid=os.getpid(),
    )
    processor = WorkerExecutionProcessor(
        session_factory=SessionLocal,
        worker_service=service,
        page_factory=page_factory,
        downloads_root=downloads_root,
        credential_client=credential_client,
        corporate_page_factory=lambda system, authorize: manager.create_monitored_corporate_page(
            system, authorize=authorize),
    )
    loop = WorkerLoop(
        service=service,
        processor=processor,
        heartbeat_every_ticks=10,
        poll_interval=1.0,
    )
    return WorkerApp(loop=loop, browser_manager=manager)


def main(*, worker_id=None, credential_client=None) -> int:
    stop_event = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_args: stop_event.set())

    app = build_worker(worker_id=worker_id, credential_client=credential_client)
    try:
        app.loop.run(stop_event=stop_event)
        return 0
    finally:
        app.browser_manager.close()


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean environment variable: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
