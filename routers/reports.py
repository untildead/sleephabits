\
import csv
from datetime import date, timedelta
from io import StringIO
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import case, cast, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.types import Float, Numeric

from db.session import get_db
from models.entities import SleepRecord, SleepStage, Subject, SubjectTag, Tag

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/aggregates")
async def aggregates(
    days: int = Query(90, ge=1, le=365),
    min_n: int = Query(3, ge=1),
    session=Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days - 1)
    base_filters = [
        SleepRecord.record_date >= cutoff,
        SleepRecord.record_date <= date.today(),
        SleepRecord.is_deleted.is_(False),
        Subject.is_deleted.is_(False),
        SleepRecord.sleep_duration >= 0.0,
        SleepRecord.sleep_duration <= 24.0,
        SleepRecord.sleep_efficiency >= 0.0,
        SleepRecord.sleep_efficiency <= 100.0,
        Subject.age >= 0,
        Subject.age <= 120,
    ]
    clean_gender = func.upper(func.trim(Subject.gender))
    gender_group = case((clean_gender.in_(["M", "F", "O"]), clean_gender), else_="O")

    gender_stmt = (
        select(
            gender_group.label("gender"),
            func.count(SleepRecord.id).label("count"),
            cast(func.round(cast(func.avg(SleepRecord.sleep_duration), Numeric), 2), Float).label("avg_duration"),
            cast(func.round(cast(func.avg(SleepRecord.sleep_efficiency), Numeric), 2), Float).label("avg_efficiency"),
        )
        .join(SleepRecord, SleepRecord.subject_id == Subject.id)
        .where(*base_filters)
        .group_by(gender_group)
        .having(func.count(SleepRecord.id) >= min_n)
        .order_by(gender_group)
    )
    gender_rows = (await session.execute(gender_stmt)).mappings().all()
    genders = [
        {
            "gender": (row["gender"] or "O"),
            "count": row["count"],
            "avg_duration": float(row["avg_duration"]) if row["avg_duration"] is not None else None,
            "avg_efficiency": float(row["avg_efficiency"]) if row["avg_efficiency"] is not None else None,
        }
        for row in gender_rows
    ]

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
            func.count(SleepRecord.id).label("count"),
            cast(func.round(cast(func.avg(SleepRecord.sleep_duration), Numeric), 2), Float).label("avg_duration"),
            cast(func.round(cast(func.avg(SleepRecord.sleep_efficiency), Numeric), 2), Float).label("avg_efficiency"),
        )
        .join(SleepRecord, SleepRecord.subject_id == Subject.id)
        .where(*base_filters)
        .group_by(age_bucket)
        .having(func.count(SleepRecord.id) >= min_n)
        .order_by(age_bucket)
    )
    age_rows = (await session.execute(age_stmt)).mappings().all()
    ages = [
        {
            "age_bucket": row["age_bucket"],
            "count": row["count"],
            "avg_duration": float(row["avg_duration"]) if row["avg_duration"] is not None else None,
            "avg_efficiency": float(row["avg_efficiency"]) if row["avg_efficiency"] is not None else None,
        }
        for row in age_rows
    ]
    return {"by_gender": genders, "by_age_bucket": ages}


@router.get("/timeseries")
async def timeseries(
    days: int = Query(90, ge=1, le=365),
    min_n: int = Query(3, ge=1),
    session=Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days - 1)
    base_filters = [
        SleepRecord.record_date >= cutoff,
        SleepRecord.record_date <= date.today(),
        SleepRecord.is_deleted.is_(False),
        Subject.is_deleted.is_(False),
        SleepRecord.sleep_duration >= 0.0,
        SleepRecord.sleep_duration <= 24.0,
        SleepRecord.sleep_efficiency >= 0.0,
        SleepRecord.sleep_efficiency <= 100.0,
        Subject.age >= 0,
        Subject.age <= 120,
    ]
    daily_stmt = (
        select(
            SleepRecord.record_date.label("date"),
            func.count(SleepRecord.id).label("count"),
            cast(func.round(cast(func.avg(SleepRecord.sleep_duration), Numeric), 2), Float).label("avg_duration"),
        )
        .join(Subject, Subject.id == SleepRecord.subject_id)
        .where(*base_filters)
        .group_by(SleepRecord.record_date)
        .having(func.count(SleepRecord.id) >= min_n)
        .order_by(SleepRecord.record_date)
    )
    daily_rows = (await session.execute(daily_stmt)).mappings().all()
    daily = [
        {"date": row["date"], "avg_duration": float(row["avg_duration"]), "count": row["count"]}
        for row in daily_rows
    ]
    return {"daily": daily}


@router.get("/distribution")
async def distribution(
    days: int = Query(90, ge=1, le=365),
    min_n: int = Query(3, ge=1),
    session=Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days - 1)
    base_filters = [
        SleepRecord.record_date >= cutoff,
        SleepRecord.record_date <= date.today(),
        SleepRecord.is_deleted.is_(False),
        Subject.is_deleted.is_(False),
        SleepRecord.sleep_duration >= 0.0,
        SleepRecord.sleep_duration <= 24.0,
        SleepRecord.sleep_efficiency >= 0.0,
        SleepRecord.sleep_efficiency <= 100.0,
        Subject.age >= 0,
        Subject.age <= 120,
    ]
    stage_stmt = (
        select(
            func.count(SleepStage.id).label("count"),
            cast(func.round(cast(func.avg(SleepStage.rem_percentage), Numeric), 2), Float).label("rem"),
            cast(func.round(cast(func.avg(SleepStage.deep_percentage), Numeric), 2), Float).label("deep"),
            cast(func.round(cast(func.avg(SleepStage.light_percentage), Numeric), 2), Float).label("light"),
        )
        .join(SleepRecord, SleepRecord.id == SleepStage.sleep_record_id)
        .join(Subject, Subject.id == SleepRecord.subject_id)
        .where(*base_filters)
    )
    stage_row = (await session.execute(stage_stmt)).mappings().first()
    if stage_row and stage_row["count"] and stage_row["count"] >= min_n:
        data = {k: float(stage_row[k] or 0) for k in ["rem", "deep", "light"]}
        if any(data.values()):
            return {"source": "sleep_stages", "count": stage_row["count"], "data": data}
    return {"source": "sleep_stages", "count": 0, "data": {"rem": 0, "deep": 0, "light": 0}}


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


@router.get("/habits_quality")
async def habits_quality(session=Depends(get_db)):
    stmt = (
        select(
            Tag.name.label("tag"),
            func.avg(SleepRecord.sleep_efficiency).label("avg_efficiency"),
            func.avg(SleepRecord.sleep_duration).label("avg_duration"),
            func.count(SleepRecord.id).label("n"),
        )
        .join(SubjectTag, SubjectTag.tag_id == Tag.id)
        .join(Subject, Subject.id == SubjectTag.subject_id)
        .join(SleepRecord, SleepRecord.subject_id == Subject.id)
        .where(
            Subject.is_deleted.is_(False),
            SleepRecord.is_deleted.is_(False),
        )
        .group_by(Tag.name)
        .order_by(func.avg(SleepRecord.sleep_efficiency).desc().nullslast())
    )
    rows = (await session.execute(stmt)).mappings().all()
    data = [
        {
            "tag": r["tag"],
            "avg_efficiency": float(r["avg_efficiency"]) if r["avg_efficiency"] is not None else 0.0,
            "avg_duration": float(r["avg_duration"]) if r["avg_duration"] is not None else 0.0,
            "n": int(r["n"]) if r["n"] is not None else 0,
        }
        for r in rows
    ]
    return {"by_tag": data}
