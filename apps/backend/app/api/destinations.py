from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import Destination
from app.repositories.destination import get_by_code, get_by_id, list_items
from app.schemas_destination import (
    DestinationCreate,
    DestinationListResponse,
    DestinationRead,
    DestinationUpdate,
)


router = APIRouter(prefix="/destinations", tags=["Destinations"])


def _read(destination: Destination) -> DestinationRead:
    return DestinationRead(
        id=destination.id,
        code=destination.code,
        name=destination.name,
        path_reference=destination.path_reference,
        enabled=destination.enabled,
        last_test_status=destination.last_test_status,
        last_test_at=destination.last_test_at,
    )


@router.post("", response_model=DestinationRead, status_code=201)
def create_destination(
    payload: DestinationCreate,
    db: Session = Depends(get_db),
):
    if not payload.path_reference.strip():
        raise ApiError(
            422,
            "DESTINATION_PATH_REQUIRED",
            "Destination path_reference is required",
        )

    if get_by_code(db, payload.code):
        raise ApiError(
            409,
            "DESTINATION_CODE_CONFLICT",
            "Destination code already exists",
        )

    destination = Destination(
        code=payload.code,
        name=payload.name,
        path_reference=payload.path_reference.strip(),
        enabled=payload.enabled,
    )
    db.add(destination)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "DESTINATION_CODE_CONFLICT",
            "Destination code already exists",
        ) from exc

    db.refresh(destination)
    return _read(destination)


@router.get("", response_model=DestinationListResponse)
def list_destinations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = list_items(db, offset=offset, limit=limit)
    return {
        "items": [_read(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.put("/{destination_id}", response_model=DestinationRead)
def update_destination(
    destination_id: int,
    payload: DestinationUpdate,
    db: Session = Depends(get_db),
):
    destination = get_by_id(db, destination_id)
    if destination is None:
        raise ApiError(404, "DESTINATION_NOT_FOUND", "Destination not found")

    existing = get_by_code(db, payload.code)
    if existing is not None and existing.id != destination_id:
        raise ApiError(
            409,
            "DESTINATION_CODE_CONFLICT",
            "Destination code already exists",
        )

    if not payload.path_reference.strip():
        raise ApiError(
            422,
            "DESTINATION_PATH_REQUIRED",
            "Destination path_reference is required",
        )

    destination.code = payload.code
    destination.name = payload.name
    destination.path_reference = payload.path_reference.strip()
    destination.enabled = payload.enabled

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "DESTINATION_CODE_CONFLICT",
            "Destination code already exists",
        ) from exc

    db.refresh(destination)
    return _read(destination)


@router.delete("/{destination_id}", status_code=204)
def delete_destination(
    destination_id: int,
    db: Session = Depends(get_db),
):
    destination = get_by_id(db, destination_id)
    if destination is None:
        raise ApiError(404, "DESTINATION_NOT_FOUND", "Destination not found")

    db.delete(destination)
    db.commit()


@router.get("/{destination_id}", response_model=DestinationRead)
def get_destination(
    destination_id: int,
    db: Session = Depends(get_db),
):
    item = get_by_id(db, destination_id)
    if item is None:
        raise ApiError(
            404,
            "DESTINATION_NOT_FOUND",
            "Destination not found",
        )
    return _read(item)
