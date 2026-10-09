from time import monotonic

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.api.automations import router as automations_router
from app.api.events import router as events_router
from app.api.diagnostics import router as diagnostics_router
from app.api.automation_versions import router as automation_versions_router
from app.api.destinations import router as destinations_router
from app.api.executions import router as executions_router
from app.config import get_settings
from app.errors import ApiError
from app.security import SESSION_COOKIE_NAME, resolve_session
from ipaddress import ip_address
from app.api.worker_credentials import router as worker_credentials_router
from app.worker_channel import worker_channel


settings = get_settings()

import asyncio
from contextlib import asynccontextmanager
from app.security import sweep_sessions


@asynccontextmanager
async def lifespan(application):
    async def cleanup():
        while True:
            sweep_sessions()
            worker_channel.sweep()
            await asyncio.sleep(5)
    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.state.started_at = monotonic()
app.state.requests_total = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    app.state.requests_total += 1
    path = request.url.path
    try:
        local_peer = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local_peer = False
    allowed_hosts = {f"127.0.0.1:{settings.port}", f"localhost:{settings.port}", f"[::1]:{settings.port}"}
    origin = request.headers.get("origin")
    mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
    if (
        not local_peer or request.headers.get("host") not in allowed_hosts
        or (origin is not None and origin not in settings.cors_origins)
        or (mutation and origin not in settings.cors_origins)
    ):
        return JSONResponse(status_code=403, content={"error": {
            "code": "LOCAL_REQUEST_REQUIRED", "message": "Acesso local autorizado obrigatório.", "details": None}})
    public_paths = {"/", "/health", "/version"}
    if request.method == "OPTIONS" or path in public_paths or path in {"/auth/login", "/auth/session", "/auth/logout"}:
        return await call_next(request)
    if path.startswith("/internal/") and worker_channel.authorized(request.headers.get("x-nexer-worker")):
        return await call_next(request)
    if resolve_session(request.cookies.get(SESSION_COOKIE_NAME)) is None:
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "AUTH_REQUIRED", "message": "Authentication required", "details": None}},
        )
    return await call_next(request)


@app.exception_handler(ApiError)
async def api_error_handler(
    request: Request, exc: ApiError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if exc.status_code == 404:
        code = "NOT_FOUND"
        message = "Route not found"
    else:
        code = f"HTTP_{exc.status_code}"
        message = "Request could not be completed"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": None,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": None,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": None,
            }
        },
    )


app.include_router(auth_router)
app.include_router(worker_credentials_router)
app.include_router(automations_router)
app.include_router(executions_router)
app.include_router(events_router)
app.include_router(diagnostics_router)
app.include_router(automation_versions_router)
app.include_router(destinations_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"api": settings.app_name, "version": settings.version}


@app.get("/metrics")
def metrics() -> dict[str, int | str | float]:
    return {
        "service": "nexer-api",
        "version": settings.version,
        "requests_total": int(app.state.requests_total),
        "uptime_seconds": round(monotonic() - app.state.started_at, 3),
    }
