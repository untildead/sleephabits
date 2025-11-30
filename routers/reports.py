\
import csv
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from db.session import get_db
from models.entities import LifestyleFactors, SleepRecord, SleepStage, Subject, SubjectTag, Tag

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/aggregates")
async def aggregates(session=Depends(get_db)):
    gender_stmt = (
        select(
            Subject.gender,
            func.avg(SleepRecord.sleep_duration).label("avg_duration"),
            func.avg(SleepRecord.sleep_efficiency).label("avg_efficiency"),
        )
        .join(SleepRecord, SleepRecord.subject_id == Subject.id)
        .where(SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False))
        .group_by(Subject.gender)
    )
    genders = (await session.execute(gender_stmt)).mappings().all()

    age_bucket = case(
        (Subject.age < 18, "menor"),
        (Subject.age.between(18, 30), "18-30"),
        (Subject.age.between(31, 45), "31-45"),
        (Subject.age.between(46, 60), "46-60"),
        (Subject.age > 60, "60+"),
        else_="desconocido",
    )
    age_stmt = (
        select(
            age_bucket.label("age_bucket"),
            func.avg(SleepRecord.sleep_duration).label("avg_duration"),
            func.avg(SleepRecord.sleep_efficiency).label("avg_efficiency"),
        )
        .join(SleepRecord, SleepRecord.subject_id == Subject.id)
        .where(SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False))
        .group_by(age_bucket)
    )
    ages = (await session.execute(age_stmt)).mappings().all()
    return {"by_gender": genders, "by_age_bucket": ages}


@router.get("/timeseries")
async def timeseries(session=Depends(get_db)):
    stmt = (
        select(
            SleepRecord.record_date.label("date"),
            func.avg(SleepRecord.sleep_duration).label("avg_duration"),
        )
        .join(Subject, Subject.id == SleepRecord.subject_id)
        .where(SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False))
        .group_by(SleepRecord.record_date)
        .order_by(SleepRecord.record_date)
    )
    rows = (await session.execute(stmt)).mappings().all()
    daily = [{"date": r["date"], "avg_duration": r["avg_duration"]} for r in rows]
    weekly_acc = {}
    for r in rows:
        dt = r["date"]
        key = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        if key not in weekly_acc:
            weekly_acc[key] = {"total": 0.0, "count": 0}
        weekly_acc[key]["total"] += r["avg_duration"]
        weekly_acc[key]["count"] += 1
    weekly = [{"week": k, "avg_duration": v["total"] / v["count"]} for k, v in sorted(weekly_acc.items())]
    return {"daily": daily, "weekly": weekly}


@router.get("/distribution")
async def distribution(session=Depends(get_db)):
    stage_stmt = select(
        func.avg(SleepStage.rem_percentage).label("rem"),
        func.avg(SleepStage.deep_percentage).label("deep"),
        func.avg(SleepStage.light_percentage).label("light"),
    ).join(SleepRecord, SleepRecord.id == SleepStage.sleep_record_id).join(Subject, Subject.id == SleepRecord.subject_id).where(
        SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False)
    )
    stage_row = (await session.execute(stage_stmt)).one_or_none()
    if stage_row and any(stage_row):
        rem, deep, light = stage_row
        return {"source": "sleep_stages", "data": {"rem": rem or 0, "deep": deep or 0, "light": light or 0}}

    tag_stmt = (
        select(Tag.name, func.count(SubjectTag.subject_id).label("count"))
        .join(SubjectTag, SubjectTag.tag_id == Tag.id)
        .join(Subject, Subject.id == SubjectTag.subject_id)
        .where(Subject.is_deleted.is_(False))
        .group_by(Tag.name)
        .order_by(Tag.name)
    )
    tags = (await session.execute(tag_stmt)).mappings().all()
    return {"source": "tags", "data": tags}


@router.get("/records.csv")
async def records_csv(session=Depends(get_db)):
    stmt = (
        select(SleepRecord)
        .options(selectinload(SleepRecord.subject))
        .where(SleepRecord.is_deleted.is_(False))
        .order_by(SleepRecord.record_date.desc())
    )
    rows: List[SleepRecord] = (await session.execute(stmt)).scalars().unique().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "subject_id", "subject_gender", "record_date", "bedtime", "wakeup_time", "sleep_duration", "sleep_efficiency", "awakenings", "attachment_url"]
    )
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.subject_id,
                r.subject.gender if r.subject else "",
                r.record_date.isoformat(),
                r.bedtime.isoformat(),
                r.wakeup_time.isoformat(),
                r.sleep_duration,
                r.sleep_efficiency,
                r.awakenings,
                r.attachment_url or "",
            ]
        )
    resp = PlainTextResponse(output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = 'attachment; filename="records.csv"'
    return resp


@router.get("/subjects.csv")
async def subjects_csv(session=Depends(get_db)):
    stmt = select(Subject).options(selectinload(Subject.tags)).order_by(Subject.id)
    rows: List[Subject] = (await session.execute(stmt)).scalars().unique().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "age", "gender", "is_deleted", "tags"])
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.name or "",
                r.age,
                r.gender,
                r.is_deleted,
                ",".join([t.name for t in r.tags]),
            ]
        )
    resp = PlainTextResponse(output.getvalue(), media_type="text/csv")
    resp.headers["Content-Disposition"] = 'attachment; filename="subjects.csv"'
    return resp
