\
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from db.session import get_db
from models.entities import Subject, SubjectTag, Tag
from models.schemas import SubjectSummary, TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=List[TagRead])
async def list_tags(session=Depends(get_db)):
    result = await session.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()


@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(tag_id: int, session=Depends(get_db)):
    tag = (await session.execute(select(Tag).where(Tag.id == tag_id))).scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tag(data: TagCreate, session=Depends(get_db)):
    tag = Tag(name=data.name)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Tag name must be unique")
    await session.refresh(tag)
    return {"id": tag.id}


@router.put("/{tag_id}")
async def put_tag(tag_id: int, data: TagCreate, session=Depends(get_db)):
    try:
        result = await session.execute(update(Tag).where(Tag.id == tag_id).values(name=data.name).returning(Tag.id))
        if result.scalar_one_or_none() is None:
            await session.rollback()
            raise HTTPException(status_code=404, detail="Tag not found")
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Tag name must be unique")
    return {"updated": True}


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, session=Depends(get_db)):
    result = await session.execute(delete(Tag).where(Tag.id == tag_id))
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Tag not found")
    await session.commit()
    return {"deleted": True}


@router.post("/subjects/{subject_id}/tags/{tag_id}")
async def assign_tag(subject_id: int, tag_id: int, session=Depends(get_db)):
    subject = (await session.execute(select(Subject).where(Subject.id == subject_id, Subject.is_deleted.is_(False)))).scalar_one_or_none()
    tag = (await session.execute(select(Tag).where(Tag.id == tag_id))).scalar_one_or_none()
    if not subject or not tag:
        raise HTTPException(status_code=400, detail="Invalid subject or tag")
    link = SubjectTag(subject_id=subject_id, tag_id=tag_id)
    session.add(link)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Could not assign (already linked?)")
    return {"assigned": True}


@router.delete("/subjects/{subject_id}/tags/{tag_id}")
async def unassign_tag(subject_id: int, tag_id: int, session=Depends(get_db)):
    result = await session.execute(delete(SubjectTag).where(SubjectTag.subject_id == subject_id, SubjectTag.tag_id == tag_id))
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Link not found")
    await session.commit()
    return {"unassigned": True}


@router.get("/subjects/{subject_id}", response_model=List[TagRead])
async def list_tags_for_subject(subject_id: int, session=Depends(get_db)):
    result = await session.execute(
        select(Tag).join(SubjectTag).where(SubjectTag.subject_id == subject_id).order_by(Tag.name)
    )
    return result.scalars().all()


@router.get("/{tag_id}/subjects", response_model=List[SubjectSummary])
async def list_subjects_for_tag(tag_id: int, session=Depends(get_db)):
    result = await session.execute(
        select(Subject)
        .options(selectinload(Subject.tags))
        .join(SubjectTag)
        .where(SubjectTag.tag_id == tag_id, Subject.is_deleted.is_(False))
    )
    return result.scalars().unique().all()
