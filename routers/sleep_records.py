\
from datetime import date
from typing import List, Optional, Type

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ValidationError

from db.session import get_db
from models.entities import SleepRecord, Subject
from models.schemas import SleepRecordCreate, SleepRecordRead, SleepRecordUpdate, compute_sleep_metrics, ensure_sleep_window

router = APIRouter(prefix="/records", tags=["records"])


def _validation_message(err: ValidationError) -> str:
    return err.errors()[0].get("msg", "Datos inválidos") if err.errors() else "Datos inválidos"


def _parse_model(model: Type[BaseModel], payload: dict):
    try:
        return model.model_validate(payload)
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=_validation_message(err))


async def _ensure_subject(session, subject_id: int):
    subject = (
        await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(False)))
    ).scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=400, detail="Sujeto no encontrado o eliminado")
    return subject


def _calculate_metrics(record_date: date, bedtime, wakeup_time, awakenings: int):
    bed_dt, wake_dt = ensure_sleep_window(record_date, bedtime, wakeup_time)
    duration, efficiency = compute_sleep_metrics(record_date, bedtime, wakeup_time, awakenings or 0)
    if not (2.0 <= duration <= 14.0):
        raise HTTPException(status_code=400, detail="La duración del sueño debe estar entre 2 y 14 horas.")
    if not (0.0 <= efficiency <= 100.0):
        raise HTTPException(status_code=400, detail="La eficiencia debe estar entre 0 y 100.")
    return bed_dt, wake_dt, round(duration, 2), round(efficiency, 2)


async def _record_query_base(session, include_deleted: bool):
    stmt = (
        select(SleepRecord)
        .options(selectinload(SleepRecord.subject))
        .join(Subject)
        .order_by(SleepRecord.record_date.desc(), SleepRecord.id.desc())
    )
    if not include_deleted:
        stmt = stmt.where(SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False))
    return stmt


@router.get("", response_model=List[SleepRecordRead])
async def list_records(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    gender: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    include_deleted: bool = Query(False),
    session=Depends(get_db),
):
    stmt = await _record_query_base(session, include_deleted)
    filters = []
    if date_from:
        filters.append(SleepRecord.record_date >= date_from)
    if date_to:
        filters.append(SleepRecord.record_date <= date_to)
    if gender:
        filters.append(Subject.gender.ilike(f"%{gender}%"))
    if subject_id:
        filters.append(SleepRecord.subject_id == subject_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    result = await session.execute(stmt)
    return result.scalars().unique().all()


@router.get("/{record_id}", response_model=SleepRecordRead)
async def get_record(
    record_id: int,
    include_deleted: bool = Query(False),
    session=Depends(get_db),
):
    stmt = await _record_query_base(session, include_deleted)
    stmt = stmt.where(SleepRecord.id == record_id)
    result = await session.execute(stmt)
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return record


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_record(payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SleepRecordCreate, payload)
    await _ensure_subject(session, data.subject_id)
    bed_dt, wake_dt, duration, efficiency = _calculate_metrics(
        data.record_date, data.bedtime, data.wakeup_time, data.awakenings
    )
    new_record = SleepRecord(
        subject_id=data.subject_id,
        record_date=data.record_date,
        bedtime=bed_dt,
        wakeup_time=wake_dt,
        sleep_duration=duration,
        sleep_efficiency=efficiency,
        awakenings=data.awakenings or 0,
        attachment_url=data.attachment_url,
        notes=data.notes,
    )
    session.add(new_record)
    await session.commit()
    await session.refresh(new_record)
    return {"id": new_record.id}


@router.put("/{record_id}")
async def put_record(record_id: int, payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SleepRecordCreate, payload)
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    await _ensure_subject(session, data.subject_id)
    bed_dt, wake_dt, duration, efficiency = _calculate_metrics(
        data.record_date, data.bedtime, data.wakeup_time, data.awakenings
    )
    record.subject_id = data.subject_id
    record.record_date = data.record_date
    record.bedtime = bed_dt
    record.wakeup_time = wake_dt
    record.sleep_duration = duration
    record.sleep_efficiency = efficiency
    record.awakenings = data.awakenings or 0
    record.attachment_url = data.attachment_url
    record.notes = data.notes
    await session.commit()
    return {"updated": True}


@router.patch("/{record_id}")
async def patch_record(record_id: int, payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SleepRecordUpdate, payload)
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado o sin cambios")
    update_data = data.model_dump(exclude_unset=True)
    if "subject_id" in update_data:
        await _ensure_subject(session, update_data["subject_id"])
        record.subject_id = update_data["subject_id"]
    recalc_keys = {"record_date", "bedtime", "wakeup_time", "awakenings", "sleep_duration", "sleep_efficiency"}
    if any(k in update_data for k in recalc_keys):
        record_date = update_data.get("record_date") or record.record_date
        bedtime = update_data.get("bedtime") or record.bedtime.time()
        wakeup_time = update_data.get("wakeup_time") or record.wakeup_time.time()
        awakenings = update_data.get("awakenings")
        if awakenings is None:
            awakenings = record.awakenings
        bed_dt, wake_dt, duration, efficiency = _calculate_metrics(record_date, bedtime, wakeup_time, awakenings)
        record.record_date = record_date
        record.bedtime = bed_dt
        record.wakeup_time = wake_dt
        record.sleep_duration = duration
        eff_value = efficiency if update_data.get("sleep_efficiency") is None else update_data["sleep_efficiency"]
        record.sleep_efficiency = round(eff_value, 2)
        record.awakenings = awakenings
    for field in ["attachment_url", "notes"]:
        if field in update_data and update_data[field] is not None:
            setattr(record, field, update_data[field])
    if "is_deleted" in update_data and update_data["is_deleted"] is not None:
        record.is_deleted = bool(update_data["is_deleted"])
    await session.commit()
    return {"updated": True}


@router.delete("/{record_id}")
async def delete_record(record_id: int, session=Depends(get_db)):
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id, SleepRecord.is_deleted.is_(False)))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado o ya eliminado")
    record.is_deleted = True
    await session.commit()
    return {"deleted": True}


@router.post("/{record_id}/restore")
async def restore_record(record_id: int, session=Depends(get_db)):
    record = (await session.execute(select(SleepRecord).where(SleepRecord.id == record_id, SleepRecord.is_deleted.is_(True)))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado o no eliminado")
    record.is_deleted = False
    await session.commit()
    return {"restored": True}
