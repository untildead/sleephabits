from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db  
from models.entities import SleepRecord
from models.schemas import UploadResponse
from utils.supabase_client import upload_file


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    try:
        url = await upload_file(file, path_prefix="sleep-records")
        return UploadResponse(public_url=url)
    except Exception as e:
        # 500 con detalle visible para depurar
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.patch("/records/{record_id}/attach")
async def attach(
    record_id: int,
    payload: UploadResponse,
    session: AsyncSession = Depends(get_db),
):
    record = (
        await session.execute(
            select(SleepRecord).where(SleepRecord.id == record_id)
        )
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record.attachment_url = payload.public_url
    await session.commit()
    return {"updated": True, "attachment_url": record.attachment_url}
