"""Executable entry point for the RelatPy Worker.

The browser factory is intentionally injected by the runtime integration layer.
This process only coordinates lifecycle and execution polling.
"""

import os
import signal
from pathlib import Path
from threading import Event

from app.database import SessionLocal
from relatpy_worker.loop import WorkerLoop
from relatpy_worker.processor import WorkerExecutionProcessor
from relatpy_worker.service import WorkerService


def build_worker() -> WorkerLoop:
    worker_id = os.getenv("RELATPY_WORKER_ID") or f"worker-{os.getpid()}"
    concurrency = int(os.getenv("RELATPY_WORKER_CONCURRENCY", "1"))
    downloads_root = Path(
        os.getenv("RELATPY_DOWNLOADS_ROOT", "./downloads")
    )

    # Browser creation is deliberately deferred. It will be provided by
    # BrowserManager in the next Etapa 1 block.
    def page_factory(*_args, **_kwargs):
        raise RuntimeError("BROWSER_MANAGER_NOT_CONFIGURED")

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
    )
    return WorkerLoop(
        service=service,
        processor=processor,
        heartbeat_every_ticks=10,
        poll_interval=1.0,
    )


def main() -> int:
    stop_event = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_args: stop_event.set())

    build_worker().run(stop_event=stop_event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
