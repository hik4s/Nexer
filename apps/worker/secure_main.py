"""Worker launched by run_local.py; bootstrap data never appears in argv/env."""
import json
import sys
from nexer_worker.credential_client import ExecutionCredentialClient
from main import main


def entrypoint():
    try:
        bootstrap = json.loads(sys.stdin.readline(4096))
        worker_id = bootstrap["worker_id"]
        if not isinstance(worker_id, str) or not worker_id.startswith("ephemeral-") or len(worker_id) > 100:
            raise ValueError()
        client = ExecutionCredentialClient(bootstrap["url"], bootstrap["capability"])
        bootstrap.clear()
    except Exception:
        raise SystemExit("WORKER_BOOTSTRAP_FAILED") from None
    return main(worker_id=worker_id, credential_client=client)


if __name__ == "__main__":
    raise SystemExit(entrypoint())
