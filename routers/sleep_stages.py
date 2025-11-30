\
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from db.session import get_db
from models.entities import SleepRecord, SleepStage
from models.schemas import SleepStageCreate, SleepStageRead, SleepStageUpdate

router = APIRouter(prefix="/sleep-stages", tags=["sleep_stages"])


async def _ensure_record(session, record_id: int):
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id, SleepRecord.is_deleted.is_(False)))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=400, detail="SleepRecord not found or deleted")
    return record


@router.get("/{stage_id}", response_model=SleepStageRead)
async def get_stage(stage_id: int, session=Depends(get_db)):
    s = (await session.execute(select(SleepStage).where(SleepStage.id == stage_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="SleepStage not found")
    return s


@router.get("/by-record/{record_id}", response_model=Optional[SleepStageRead])
async def get_stage_by_record(record_id: int, session=Depends(get_db)):
    return (await session.execute(select(SleepStage).where(SleepStage.sleep_record_id == record_id))).scalar_one_or_none()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_stage(data: SleepStageCreate, session=Depends(get_db)):
    await _ensure_record(session, data.sleep_record_id)
    stage = SleepStage(**data.model_dump())
    session.add(stage)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="SleepStage already exists for this record")
    await session.refresh(stage)
    return {"id": stage.id}


@router.put("/{stage_id}")
async def put_stage(stage_id: int, data: SleepStageCreate, session=Depends(get_db)):
    await _ensure_record(session, data.sleep_record_id)
    stage = (await session.execute(select(SleepStage).where(SleepStage.id == stage_id))).scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="SleepStage not found")
    stage.sleep_record_id = data.sleep_record_id
    stage.rem_percentage = data.rem_percentage
    stage.deep_percentage = data.deep_percentage
    stage.light_percentage = data.light_percentage
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Another SleepStage already exists for this record")
    return {"updated": True}


@router.patch("/{stage_id}")
async def patch_stage(stage_id: int, data: SleepStageUpdate, session=Depends(get_db)):
    payload = data.model_dump(exclude_unset=True)
    stage = (await session.execute(select(SleepStage).where(SleepStage.id == stage_id))).scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="SleepStage not found or no changes")
    if "sleep_record_id" in payload:
        await _ensure_record(session, payload["sleep_record_id"])
        stage.sleep_record_id = payload["sleep_record_id"]
    for field in ["rem_percentage", "deep_percentage", "light_percentage"]:
        if field in payload and payload[field] is not None:
            setattr(stage, field, payload[field])
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Another SleepStage already exists for this record")
    return {"updated": True}


@router.delete("/{stage_id}")
async def delete_stage(stage_id: int, session=Depends(get_db)):
    result = await session.execute(delete(SleepStage).where(SleepStage.id == stage_id))
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=404, detail="SleepStage not found")
    await session.commit()
    return {"deleted": True}
