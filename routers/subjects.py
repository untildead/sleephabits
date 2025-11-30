\
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import selectinload

from db.session import get_db
from models.entities import Subject, Tag, SubjectTag
from models.schemas import SubjectCreate, SubjectRead, SubjectUpdate

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/subjects", tags=["subjects"])


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
    return result.scalars().unique().all()


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
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


async def _load_tags(session, tag_ids: List[int]):
    if not tag_ids:
        return []
    result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tag IDs are invalid")
    return tags


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subject(data: SubjectCreate, session=Depends(get_db)):
    if data.age < 0:
        raise HTTPException(status_code=400, detail="age must be >= 0")
    new_subject = Subject(name=data.name, age=data.age, gender=data.gender)
    new_subject.tags = await _load_tags(session, data.tag_ids)
    session.add(new_subject)
    await session.commit()
    await session.refresh(new_subject)
    return {"id": new_subject.id}


@router.put("/{subject_id}")
async def put_subject(subject_id: int, data: SubjectCreate, session=Depends(get_db)):
    result = await session.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    subject.name = data.name
    subject.age = data.age
    subject.gender = data.gender
    subject.tags = await _load_tags(session, data.tag_ids)
    await session.commit()
    return {"updated": True}


@router.patch("/{subject_id}")
async def patch_subject(subject_id: int, data: SubjectUpdate, session=Depends(get_db)):
    result = await session.execute(select(Subject).options(selectinload(Subject.tags)).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found or no changes")
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
        raise HTTPException(status_code=404, detail="Subject not found")
    form = await request.form()
    tag_ids = [int(t) for t in form.getlist("tag_ids") if t not in ("", None)] if "tag_ids" in form else []
    update_data = SubjectUpdate(
        name=form.get("name") or None,
        age=int(form.get("age")) if form.get("age") not in (None, "") else None,
        gender=form.get("gender") or None,
        tag_ids=tag_ids,
    )
    payload = update_data.model_dump(exclude_unset=True)
    if "age" in payload and payload["age"] is not None and payload["age"] < 0:
        raise HTTPException(status_code=400, detail="age must be >= 0")
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
    return templates.TemplateResponse("partials/subjects_table.html", {"request": request, "subjects": subjects})


@router.delete("/{subject_id}")
async def delete_subject(subject_id: int, session=Depends(get_db)):
    result = await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(False)))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found or already deleted")
    subject.is_deleted = True
    await session.commit()
    return {"deleted": True}


@router.post("/{subject_id}/restore")
async def restore_subject(subject_id: int, session=Depends(get_db)):
    result = await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(True)))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found or not deleted")
    subject.is_deleted = False
    await session.commit()
    return {"restored": True}
