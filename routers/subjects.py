\
from typing import List, Optional, Type

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ValidationError

from db.session import get_db
from models.entities import Subject, Tag, SubjectTag
from models.schemas import SubjectCreate, SubjectRead, SubjectUpdate

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _validation_message(err: ValidationError) -> str:
    return err.errors()[0].get("msg", "Datos inválidos") if err.errors() else "Datos inválidos"


def _parse_model(model: Type[BaseModel], payload: dict):
    try:
        return model.model_validate(payload)
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=_validation_message(err))


def _normalize_subject(subject: Subject):
    if subject.name:
        subject.name = " ".join(subject.name.split())
    gender = (subject.gender or "").strip().upper()
    subject.gender = gender if gender in {"M", "F", "O"} else "O"


@router.get("", response_model=List[SubjectRead])
async def list_subjects(
    gender: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None, ge=0),
    age_max: Optional[int] = Query(None, ge=0),
    q: Optional[str] = Query(None, description="Texto de búsqueda por nombre/género/tag"),
    include_deleted: bool = Query(False),
    session=Depends(get_db),
):
    stmt = select(Subject).options(selectinload(Subject.tags)).order_by(Subject.id)
    filters = []
    if not include_deleted:
        filters.append(Subject.is_deleted.is_(False))
    if gender:
        filters.append(Subject.gender.ilike(f"%{gender}%"))
    if age_min is not None:
        filters.append(Subject.age >= age_min)
    if age_max is not None:
        filters.append(Subject.age <= age_max)
    if q:
        tag_exists = exists().where(
            and_(SubjectTag.subject_id == Subject.id, SubjectTag.tag_id == Tag.id, Tag.name.ilike(f"%{q}%"))
        )
        filters.append(
            or_(
                Subject.name.ilike(f"%{q}%"),
                Subject.gender.ilike(f"%{q}%"),
                tag_exists,
            )
        )
    if filters:
        stmt = stmt.where(and_(*filters))
    result = await session.execute(stmt)
    subjects = result.scalars().unique().all()
    for s in subjects:
        _normalize_subject(s)
    return subjects


@router.get("/{subject_id}", response_model=SubjectRead)
async def get_subject(
    subject_id: int,
    include_deleted: bool = Query(False),
    session=Depends(get_db),
):
    stmt = select(Subject).options(selectinload(Subject.tags)).where(Subject.id == subject_id)
    if not include_deleted:
        stmt = stmt.where(Subject.is_deleted.is_(False))
    result = await session.execute(stmt)
    subject = result.scalars().first()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado")
    _normalize_subject(subject)
    return subject


async def _load_tags(session, tag_ids: List[int]):
    if not tag_ids:
        return []
    result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="Uno o más tags no existen")
    return tags


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subject(payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SubjectCreate, payload)
    new_subject = Subject(name=data.name, age=data.age, gender=data.gender)
    new_subject.tags = await _load_tags(session, data.tag_ids)
    session.add(new_subject)
    await session.commit()
    await session.refresh(new_subject)
    return {"id": new_subject.id}


@router.put("/{subject_id}")
async def put_subject(subject_id: int, payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SubjectCreate, payload)
    result = await session.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado")
    subject.name = data.name
    subject.age = data.age
    subject.gender = data.gender
    subject.tags = await _load_tags(session, data.tag_ids)
    await session.commit()
    return {"updated": True}


@router.patch("/{subject_id}")
async def patch_subject(subject_id: int, payload: dict = Body(...), session=Depends(get_db)):
    data = _parse_model(SubjectUpdate, payload)
    result = await session.execute(select(Subject).options(selectinload(Subject.tags)).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado o sin cambios")
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        subject.name = update_data["name"]
    if "age" in update_data:
        subject.age = update_data["age"]
    if "gender" in update_data:
        subject.gender = update_data["gender"]
    if "is_deleted" in update_data and update_data["is_deleted"] is not None:
        subject.is_deleted = bool(update_data["is_deleted"])
    if "tag_ids" in update_data and update_data["tag_ids"] is not None:
        subject.tags = await _load_tags(session, update_data["tag_ids"])
    await session.commit()
    return {"updated": True}


@router.post("/{subject_id}/update", response_class=HTMLResponse)
async def update_subject_form(subject_id: int, request: Request, session=Depends(get_db)):
    result = await session.execute(select(Subject).options(selectinload(Subject.tags)).where(Subject.id == subject_id, Subject.is_deleted.is_(False)))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado")
    form = await request.form()
    tag_ids = [int(t) for t in form.getlist("tag_ids") if t not in ("", None)] if "tag_ids" in form else []
    try:
        update_data = SubjectUpdate(
            name=form.get("name") or None,
            age=int(form.get("age")) if form.get("age") not in (None, "") else None,
            gender=form.get("gender") or None,
            tag_ids=tag_ids,
        )
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=_validation_message(err))
    payload = update_data.model_dump(exclude_unset=True)
    if "name" in payload:
        subject.name = payload["name"]
    if "age" in payload:
        subject.age = payload["age"]
    if "gender" in payload:
        subject.gender = payload["gender"]
    if "tag_ids" in payload:
        subject.tags = await _load_tags(session, payload["tag_ids"])
    await session.commit()
    stmt = select(Subject).options(selectinload(Subject.tags)).where(Subject.is_deleted.is_(False)).order_by(Subject.id)
    subjects = (await session.execute(stmt)).scalars().unique().all()
    for s in subjects:
        _normalize_subject(s)
    return templates.TemplateResponse("partials/subjects_table.html", {"request": request, "subjects": subjects})


@router.delete("/{subject_id}")
async def delete_subject(subject_id: int, session=Depends(get_db)):
    result = await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(False)))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado o ya eliminado")
    subject.is_deleted = True
    await session.commit()
    return {"deleted": True}


@router.post("/{subject_id}/restore")
async def restore_subject(subject_id: int, session=Depends(get_db)):
    result = await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(True)))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Sujeto no encontrado o no eliminado")
    subject.is_deleted = False
    await session.commit()
    return {"restored": True}
