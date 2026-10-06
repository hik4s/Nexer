from fastapi import FastAPI


app = FastAPI(title="RelatPy API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return the minimum liveness contract for the local API."""
    return {"status": "ok"}
