from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.config import get_settings, Settings
from app.database import get_db
from app.errors import ApiError
from app.models import Artifact, Execution, ExecutionAutomation
from app.services.execution_artifacts import open_artifact

router = APIRouter(prefix='/executions', tags=['Artifacts'])


def records(execution_id):
    return select(Artifact).join(ExecutionAutomation).where(
        ExecutionAutomation.execution_id == execution_id,
        ExecutionAutomation.status == 'SUCCEEDED', Artifact.type == 'VALIDATED_FILE')


@router.get('/{execution_id}/artifacts')
def list_artifacts(execution_id: int, response: Response, db: Session = Depends(get_db)):
    if db.get(Execution, execution_id) is None:
        raise ApiError(404, 'EXECUTION_NOT_FOUND', 'Execução não encontrada.')
    response.headers['Cache-Control'] = 'no-store'
    return {'items': [dict(id=row.id, execution_automation_id=row.execution_automation_id,
                           filename=row.filename, size=row.size, checksum=row.checksum)
                      for row in db.scalars(records(execution_id).order_by(Artifact.id))]}


@router.get('/{execution_id}/artifacts/{artifact_id}/download')
def download_artifact(execution_id: int, artifact_id: int, db: Session = Depends(get_db),
                      settings: Settings = Depends(get_settings)):
    row = db.scalar(records(execution_id).where(Artifact.id == artifact_id))
    if row is None:
        raise ApiError(404, 'ARTIFACT_NOT_FOUND', 'Arquivo não encontrado nesta execução.')
    try:
        if row.size is None or not row.checksum:
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        handle, size, _ = open_artifact(settings.downloads_root, execution_id,
            row.execution_automation_id, row.filename, size=row.size, checksum=row.checksum)
    except RuntimeError:
        raise ApiError(409, 'ARTIFACT_UNAVAILABLE', 'Arquivo indisponível ou alterado após a validação.') from None

    def chunks():
        try:
            while chunk := handle.read(1024 * 1024):
                yield chunk
        finally:
            handle.close()

    return StreamingResponse(chunks(), media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row.filename, safe=''),
        'Content-Length': str(size), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    }, background=BackgroundTask(handle.close))
