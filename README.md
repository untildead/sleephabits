# SleepHabits

FastAPI + PostgreSQL/SQLite + Supabase Storage + Jinja2/HTMX/Tailwind for tracking sleep habits with dashboards and CSV exports.

## Arquitectura
- Backend: FastAPI (async), SQLAlchemy 2.0 (dual driver: `DATABASE_URL` Postgres en Supabase o SQLite local `sqlite+aiosqlite:///./dev.db`).
- Almacenamiento de adjuntos: Supabase Storage (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, bucket `SUPABASE_BUCKET`, por defecto `sleep-uploads`).
- Frontend: Jinja2 + HTMX + Tailwind via CDN + Chart.js.
- Despliegue sugerido: Render (Procfile + render.yaml) ejecutando `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Dataset: puedes cargar datos propios o el set de Kaggle “Sleep Health and Lifestyle” via scripts/requests a `/api/subjects` y `/api/records`.
- URL pública: agrega aquí la URL de Render/Railway/Replit cuando despliegues.

## Rutas principales
- HTML público: `/` (redirige a dashboard), `/subjects`, `/records`, `/dashboard`.
- API JSON (prefijo `/api`):
  - CRUD Subjects: `/api/subjects` (filtros `gender`, `age_min`, `age_max`, `q`), soft-delete/restaurar.
  - CRUD Records: `/api/records` (filtros `date_from`, `date_to`, `gender`, `subject_id`), soft-delete/restaurar.
  - Sleep stages: `/api/sleep-stages`, Lifestyle factors `/api/lifestyle-factors`, Tags `/api/tags` (+ asignación N:M).
  - Subidas Supabase: `POST /api/uploads` (multipart) → `{"public_url": ...}`, `PATCH /api/uploads/records/{id}/attach`.
  - Reportes JSON: `/api/reports/aggregates`, `/api/reports/timeseries`, `/api/reports/distribution`.
  - Export CSV: `/api/reports/subjects.csv`, `/api/reports/records.csv`.
- Documentación interactiva: `/docs`.

## Validaciones de negocio
- `sleep_duration` en horas `0 < x ≤ 24` (Pydantic + constraint DB).
- `sleep_efficiency` en % `0 ≤ x ≤ 100` (Pydantic + constraint DB).
- `wakeup_time` siempre posterior a `bedtime` permitiendo cruce de medianoche (se suma día automáticamente).
- FK obligatoria `sleep_records.subject_id → subjects.id`; soft-delete en Subject/Record.

## Configuración de entorno
| Variable | Descripción |
| --- | --- |
| `DATABASE_URL` | Postgres (Supabase) `postgresql://...` o SQLite local `sqlite+aiosqlite:///./dev.db` (fallback si no se define). |
| `SUPABASE_URL` | URL de tu proyecto Supabase. |
| `SUPABASE_ANON_KEY` | Clave anónima de Supabase para Storage. |
| `SUPABASE_BUCKET` | Bucket de Storage (por defecto `sleep-uploads`). |

## Ejecución local (SQLite)
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
set DATABASE_URL=sqlite+aiosqlite:///./dev.db  # o export en Linux/Mac
uvicorn main:app --reload
# ó ./scripts/dev_run.sh
```
- Nota: si venías de la versión previa en SQLite, borra `suenohabitos.db` para recrear con el nuevo esquema.
- Swagger: http://127.0.0.1:8000/docs
- HTML: http://127.0.0.1:8000/subjects, /records, /dashboard

## Configurar Supabase
1. Crea proyecto y copia `SUPABASE_URL` y `SUPABASE_ANON_KEY`.
2. En Storage, crea bucket público `sleep-uploads` (o el nombre que prefieras y define `SUPABASE_BUCKET`).  
3. Usa la `DATABASE_URL` de Supabase (formato `postgresql://...`) en Render/producción.

## Despliegue en Render
1. Conecta el repo a Render.
2. Usa `render.yaml` o configura manualmente:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Env vars: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_BUCKET`.
3. Verifica `/docs` y las páginas HTML públicas.

## Notas de frontend
- Tailwind + HTMX para formularios y filtros dinámicos (tablas en `/subjects` y `/records` se refrescan vía HTMX).
- Dashboard usa Chart.js con 3 gráficas: serie de duración, barras de eficiencia por género y doughnut de distribución de etapas (o tags si no hay etapas).
- Botones “Exportar CSV” en subjects/records.

## Checklist de prueba manual
- [ ] Crear Subject desde HTML y vía POST `/api/subjects`.
- [ ] Crear SleepRecord desde HTML y vía POST `/api/records` (validar cruce de medianoche).
- [ ] Adjuntar archivo a un SleepRecord (POST `/api/uploads` + PATCH attach) y verlo en la tabla.
- [ ] Filtrar registros por fecha y género en `/records` y `/api/records`.
- [ ] Exportar CSV de subjects y records y verificar cabeceras.
- [ ] Ver dashboard con datos de prueba y gráficas cargadas.
- [ ] Soft-delete y restaurar subject/record desde botones HTML y API.

## Capturas
Incluye capturas de `/docs`, `/subjects`, `/records` y `/dashboard` cuando despliegues en Render (colócalas en README o carpeta `static/`).
