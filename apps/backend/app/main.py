from time import monotonic

from fastapi import FastAPI, Request


API_NAME = "RelatPy API"
API_VERSION = "0.1.0"

app = FastAPI(title=API_NAME, version=API_VERSION)
app.state.started_at = monotonic()
app.state.requests_total = 0


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    app.state.requests_total += 1
    return await call_next(request)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": API_NAME, "version": API_VERSION}


@app.get("/health")
def health() -> dict[str, str]:
    """Return the minimum liveness contract for the local API."""
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"api": API_NAME, "version": API_VERSION}


@app.get("/metrics")
def metrics() -> dict[str, int | str | float]:
    return {
        "service": "relatpy-api",
        "version": API_VERSION,
        "requests_total": int(app.state.requests_total),
        "uptime_seconds": round(monotonic() - app.state.started_at, 3),
    }
