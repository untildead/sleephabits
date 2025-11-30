from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import selectinload

from db.db import init_db
from db.session import get_db
from models.entities import SleepRecord, Subject, SubjectTag, Tag
from routers.lifestyle_factors import router as lf_router
from routers.reports import router as reports_router
from routers.sleep_records import router as records_router
from routers.sleep_stages import router as stages_router
from routers.subjects import router as subjects_router
from routers.tags import router as tags_router
from routers.uploads import router as uploads_router

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Sueno y Habitos", version="1.0.0", lifespan=lifespan)

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")

# API Routers (JSON)
app.include_router(subjects_router, prefix="/api")
app.include_router(records_router, prefix="/api")
app.include_router(stages_router, prefix="/api")
app.include_router(lf_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")


async def _subject_filters_stmt(
    gender: Optional[str],
    age_min: Optional[int],
    age_max: Optional[int],
    q: Optional[str],
    include_deleted: bool,
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
        filters.append(or_(Subject.name.ilike(f"%{q}%"), Subject.gender.ilike(f"%{q}%"), tag_exists))
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt


async def _records_stmt(
    date_from: Optional[date],
    date_to: Optional[date],
    gender: Optional[str],
    subject_id: Optional[int],
    include_deleted: bool,
):
    stmt = (
        select(SleepRecord)
        .options(selectinload(SleepRecord.subject))
        .join(Subject)
        .order_by(SleepRecord.record_date.desc(), SleepRecord.id.desc())
    )
    filters = []
    if not include_deleted:
        filters.extend([SleepRecord.is_deleted.is_(False), Subject.is_deleted.is_(False)])
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
    return stmt


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    return RedirectResponse(url="/dashboard")


@app.get("/subjects", response_class=HTMLResponse, include_in_schema=False)
async def subjects_page(
    request: Request,
    gender: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None),
    age_max: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    session=Depends(get_db),
):
    stmt = await _subject_filters_stmt(gender, age_min, age_max, q, include_deleted=False)
    subjects = (await session.execute(stmt)).scalars().unique().all()
    all_tags = (await session.execute(select(Tag).order_by(Tag.name))).scalars().all()
    return templates.TemplateResponse(
        "subjects.html",
        {
            "request": request,
            "subjects": subjects,
            "tags": all_tags,
            "filters": {"gender": gender or "", "age_min": age_min or "", "age_max": age_max or "", "q": q or ""},
        },
    )


@app.get("/partials/subjects-table", response_class=HTMLResponse, include_in_schema=False)
async def subjects_table_partial(
    request: Request,
    gender: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None),
    age_max: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    session=Depends(get_db),
):
    stmt = await _subject_filters_stmt(gender, age_min, age_max, q, include_deleted=False)
    subjects = (await session.execute(stmt)).scalars().unique().all()
    return templates.TemplateResponse("partials/subjects_table.html", {"request": request, "subjects": subjects})


@app.get("/subjects/{subject_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def subject_edit_partial(request: Request, subject_id: int, session=Depends(get_db)):
    subject = (
        await session.execute(
            select(Subject).options(selectinload(Subject.tags)).where(Subject.id == subject_id, Subject.is_deleted.is_(False))
        )
    ).scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    all_tags = (await session.execute(select(Tag).order_by(Tag.name))).scalars().all()
    return templates.TemplateResponse("partials/subject_form.html", {"request": request, "subject": subject, "tags": all_tags})


@app.get("/records", response_class=HTMLResponse, include_in_schema=False)
async def records_page(
    request: Request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    gender: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    session=Depends(get_db),
):
    stmt = await _records_stmt(date_from, date_to, gender, subject_id, include_deleted=False)
    records = (await session.execute(stmt)).scalars().unique().all()
    subjects = (await session.execute(select(Subject).where(Subject.is_deleted.is_(False)).order_by(Subject.id))).scalars().all()
    return templates.TemplateResponse(
        "records.html",
        {
            "request": request,
            "records": records,
            "subjects": subjects,
            "filters": {
                "date_from": date_from.isoformat() if date_from else "",
                "date_to": date_to.isoformat() if date_to else "",
                "gender": gender or "",
                "subject_id": subject_id or "",
            },
        },
    )


@app.get("/partials/records-table", response_class=HTMLResponse, include_in_schema=False)
async def records_table_partial(
    request: Request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    gender: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    session=Depends(get_db),
):
    stmt = await _records_stmt(date_from, date_to, gender, subject_id, include_deleted=False)
    records = (await session.execute(stmt)).scalars().unique().all()
    return templates.TemplateResponse("partials/records_table.html", {"request": request, "records": records})


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return HTMLResponse(f"<h1>Error</h1><p>{exc.detail}</p>", status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": exc.errors()}, status_code=422)
    return HTMLResponse("<h1>Datos inválidos</h1><p>Revisa el formulario.</p>", status_code=422)
