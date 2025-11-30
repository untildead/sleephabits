\
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update

from db.session import get_db
from models.entities import LifestyleFactors, SleepRecord
from models.schemas import LifestyleFactorsCreate, LifestyleFactorsRead, LifestyleFactorsUpdate

router = APIRouter(prefix="/lifestyle-factors", tags=["lifestyle_factors"])


async def _get_record(session, record_id: int):
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id, SleepRecord.is_deleted.is_(False)))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=400, detail="SleepRecord not found or deleted")
    return record


@router.get("/{lf_id}", response_model=LifestyleFactorsRead)
async def get_lf(lf_id: int, session=Depends(get_db)):
    lf = (await session.execute(select(LifestyleFactors).where(LifestyleFactors.id == lf_id))).scalar_one_or_none()
    if not lf:
        raise HTTPException(status_code=404, detail="LifestyleFactors not found")
    return lf


@router.get("/by-record/{record_id}", response_model=Optional[LifestyleFactorsRead])
async def get_lf_by_record(record_id: int, session=Depends(get_db)):
    return (await session.execute(select(LifestyleFactors).where(LifestyleFactors.sleep_record_id == record_id))).scalar_one_or_none()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lf(data: LifestyleFactorsCreate, session=Depends(get_db)):
    await _get_record(session, data.sleep_record_id)
    existing = (await session.execute(select(LifestyleFactors).where(LifestyleFactors.sleep_record_id == data.sleep_record_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="LifestyleFactors already exists for this record")
    lf = LifestyleFactors(**data.model_dump())
    session.add(lf)
    await session.commit()
    await session.refresh(lf)
    return {"id": lf.id}


@router.put("/{lf_id}")
async def put_lf(lf_id: int, data: LifestyleFactorsCreate, session=Depends(get_db)):
    await _get_record(session, data.sleep_record_id)
    lf = (await session.execute(select(LifestyleFactors).where(LifestyleFactors.id == lf_id))).scalar_one_or_none()
    if not lf:
        raise HTTPException(status_code=404, detail="LifestyleFactors not found")
    lf.sleep_record_id = data.sleep_record_id
    lf.caffeine_consumption = data.caffeine_consumption
    lf.alcohol_consumption = data.alcohol_consumption
    lf.smoking_status = data.smoking_status
    lf.exercise_frequency = data.exercise_frequency
    await session.commit()
    return {"updated": True}


@router.patch("/{lf_id}")
async def patch_lf(lf_id: int, data: LifestyleFactorsUpdate, session=Depends(get_db)):
    payload = data.model_dump(exclude_unset=True)
    lf = (await session.execute(select(LifestyleFactors).where(LifestyleFactors.id == lf_id))).scalar_one_or_none()
    if not lf:
        raise HTTPException(status_code=404, detail="LifestyleFactors not found or no changes")
    if "sleep_record_id" in payload:
        await _get_record(session, payload["sleep_record_id"])
        lf.sleep_record_id = payload["sleep_record_id"]
    for field in ["caffeine_consumption", "alcohol_consumption", "smoking_status", "exercise_frequency"]:
        if field in payload and payload[field] is not None:
            setattr(lf, field, payload[field])
    await session.commit()
    return {"updated": True}


@router.delete("/{lf_id}")
async def delete_lf(lf_id: int, session=Depends(get_db)):
    result = await session.execute(delete(LifestyleFactors).where(LifestyleFactors.id == lf_id))
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=404, detail="LifestyleFactors not found")
    await session.commit()
    return {"deleted": True}
