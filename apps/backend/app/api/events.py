import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.enums import ExecutionStatus
from app.errors import ApiError
from app.repositories.event import list_after
from app.repositories.execution import get_by_id


router = APIRouter(prefix="/executions", tags=["Executions"])


_TERMINAL_STATUSES = {
    ExecutionStatus.SUCCEEDED.value,
    ExecutionStatus.PARTIAL.value,
    ExecutionStatus.FAILED.value,
    ExecutionStatus.CANCELLED.value,
}


def _parse_last_event_id(request: Request) -> int:
    raw = request.headers.get("Last-Event-ID")
    if raw is None:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return 0
    return max(value, 0)


@router.get("/{execution_id}/events")
async def execution_events(
    execution_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    execution = get_by_id(db, execution_id)
    if execution is None:
        raise ApiError(404, "EXECUTION_NOT_FOUND", "Execution not found")

    last_event_id = _parse_last_event_id(request)

    stream_session_factory = sessionmaker(
        bind=db.get_bind(),
        autoflush=False,
        autocommit=False,
    )

    async def stream():
        nonlocal last_event_id
        stream_db = stream_session_factory()
        try:
            while True:
                events = list_after(
                    stream_db,
                    execution_id=execution_id,
                    after_id=last_event_id,
                )
                for event in events:
                    payload = event.payload if event.payload is not None else {}
                    data = json.dumps(payload, ensure_ascii=False)
                    yield (
                        f"id: {event.id}\n"
                        f"event: {event.type}\n"
                        f"data: {data}\n\n"
                    )
                    last_event_id = event.id

                current = get_by_id(stream_db, execution_id)
                if current is None:
                    break

                if current.status in _TERMINAL_STATUSES:
                    break

                if await request.is_disconnected():
                    break

                stream_db.expire_all()
                await asyncio.sleep(0.25)
        finally:
            stream_db.close()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
