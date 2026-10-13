"""Test-only control boundary around the real launcher and real idle worker."""
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
for relative in ("apps/backend", "apps/worker", "apps/runtime", "scripts"):
    sys.path.insert(0, str(ROOT / relative))


def main():
    import uvicorn
    import run_local
    from app.database import engine
    from app.models import Base
    Base.metadata.create_all(engine)
    engine.dispose()

    def controlled_server(application, **options):
        server = uvicorn.Server(uvicorn.Config(application, **options))
        def control():
            command = sys.stdin.readline().strip()
            if command == "crash":
                os._exit(23)  # Simulate parent loss; inherited worker pipe must reach EOF.
            if command == "kill-worker":
                from app.database import SessionLocal
                from app.models import Worker
                from sqlalchemy import select
                import signal
                with SessionLocal() as db:
                    pid = db.scalar(select(Worker.pid))
                os.kill(pid, signal.SIGTERM)  # Windows forced exit of this fixture's worker only.
            server.should_exit = True
        threading.Thread(target=control, daemon=True).start()
        server.run()

    # Only replace the server control boundary; launcher bootstrap, API,
    # production gates, worker loop and Edge remain real.
    uvicorn.run = controlled_server
    sys.argv = [sys.argv[0], "--workers", os.getenv("NEXER_TEST_WORKERS", "1")]
    run_local.main()


if __name__ == "__main__":
    main()
