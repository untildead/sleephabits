# 🌙 SleepHabits

Sistema completo para **rastrear y analizar hábitos de sueño** con API REST, panel de control interactivo y reportes avanzados.

**Stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL/SQLite + Jinja2 + HTMX + Tailwind + Chart.js

---

## 📋 Características

- **CRUD completo** de Sujetos y Registros de Sueño con soft-delete
- **API REST documentada** (Swagger en `/docs`)
- **Dashboard interactivo** con gráficas en Chart.js (duración, eficiencia, etapas)
- **Filtros avanzados** por género, edad, fechas, etiquetas
- **Adjuntos de archivos** vía Supabase Storage
- **Exportación CSV** de Sujetos y Registros
- **Reportes JSON** (agregados, series de tiempo, distribuciones)
- **Etiquetas y Factores de Estilo de Vida** (N:M relaciones)
- **Validaciones de negocio** en la base de datos y API
- **UI responsiva** con HTMX para actualización dinámica

---

## Arquitectura

```
Frontend (HTML/HTMX/Tailwind)
           ↓
    FastAPI Routers
    ├── /api/subjects        (CRUD + filtros)
    ├── /api/records         (CRUD + filtros)
    ├── /api/sleep-stages    (Etapas del sueño)
    ├── /api/lifestyle-factors (Factores de estilo de vida)
    ├── /api/tags            (Etiquetas N:M)
    ├── /api/uploads         (Supabase Storage)
    └── /api/reports         (Agregados, timeseries, CSV)
           ↓
  SQLAlchemy ORM (Async)
           ↓
  PostgreSQL (Supabase) ║ SQLite (local dev)
```

---

## Requisitos

- Python 3.9+
- pip

**Dependencias principales:** FastAPI, SQLAlchemy, Jinja2, HTMX, Tailwind CSS, Chart.js

---

## Instalación y Ejecución Local

### 1. Clonar y preparar entorno

```bash
# Windows PowerShell
git clone <repo-url>
cd sleephabits-main
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Base de datos (opcional, por defecto SQLite local)
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Supabase Storage (opcional, para adjuntos)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_BUCKET=sleep-uploads
```

### 3. Ejecutar la aplicación

```bash
# Desarrollo (con recarga automática)
uvicorn main:app --reload

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

**URLs principales:**
- Dashboard: http://localhost:8000/dashboard
- Sujetos: http://localhost:8000/subjects
- Registros: http://localhost:8000/records
- API Docs: http://localhost:8000/docs

---

## Datos de Prueba

Carga datos de prueba con 20 personajes animados y 150+ registros:

```bash
python seed_data.py
```

Los datos incluyen:
- 20 sujetos (Mickey, Naruto, Goku, etc.)
- 6 etiquetas comunes (Ejercicio, Café, Pantallas, etc.)
- 150+ registros de sueño distribuidos aleatoriamente

---

## API REST - Endpoints Principales

### Sujetos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/subjects` | Listar sujetos (filtros: `gender`, `age_min`, `age_max`, `q`) |
| POST | `/api/subjects` | Crear sujeto |
| GET | `/api/subjects/{id}` | Obtener sujeto |
| PATCH | `/api/subjects/{id}` | Actualizar sujeto |
| DELETE | `/api/subjects/{id}` | Soft-delete |
| PATCH | `/api/subjects/{id}/restore` | Restaurar |

### Registros de Sueño
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/records` | Listar (filtros: `date_from`, `date_to`, `gender`, `subject_id`) |
| POST | `/api/records` | Crear registro |
| GET | `/api/records/{id}` | Obtener registro |
| PATCH | `/api/records/{id}` | Actualizar |
| DELETE | `/api/records/{id}` | Soft-delete |
| PATCH | `/api/records/{id}/restore` | Restaurar |

### Reportes y Exportación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/reports/aggregates` | Estadísticas agregadas (JSON) |
| GET | `/api/reports/timeseries` | Series de tiempo (JSON) |
| GET | `/api/reports/distribution` | Distribuciones (JSON) |
| GET | `/api/reports/subjects.csv` | Exportar sujetos (CSV) |
| GET | `/api/reports/records.csv` | Exportar registros (CSV) |

### Otros
| Endpoint | Descripción |
|----------|-------------|
| `/api/tags` | CRUD de etiquetas |
| `/api/sleep-stages` | CRUD de etapas del sueño |
| `/api/lifestyle-factors` | CRUD de factores de estilo de vida |
| `/api/uploads` | POST multipart para subir archivos a Supabase |

**Documentación interactiva:** http://localhost:8000/docs

---

## Validaciones de Negocio

| Campo | Validación |
|-------|-----------|
| `sleep_duration` | 0 < duración ≤ 24 horas |
| `sleep_efficiency` | 0 ≤ eficiencia ≤ 100 % |
| `wakeup_time` | Siempre posterior a `bedtime` (permite cruce de medianoche) |
| `subject_id` | FK obligatoria en `sleep_records` |
| Soft-delete | Sujetos y registros pueden marcarse como eliminados sin borrar datos |

---

## Despliegue en Producción (Render)

### 1. Preparar el repositorio

Asegúrate de que tengas `Procfile` o `render.yaml`:

```yaml
# render.yaml
services:
  - type: web
    name: sleephabits
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        scope: shared
      - key: SUPABASE_URL
        scope: shared
      - key: SUPABASE_ANON_KEY
        scope: shared
      - key: SUPABASE_BUCKET
        scope: shared
```

### 2. Configurar en Render

1. Conecta tu repositorio a Render
2. Define las variables de entorno (DATABASE_URL, SUPABASE_*)
3. Deploy automático en cada push a `main`

### 3. Configurar Supabase (Opcional)

Si usas Supabase para base de datos y almacenamiento:

1. Crea proyecto en https://supabase.com
2. Copia `SUPABASE_URL` y `SUPABASE_ANON_KEY`
3. Crea bucket público `sleep-uploads` en Storage
4. Usa `DATABASE_URL` de Supabase en producción

---

## Estructura del Proyecto

```
sleephabits-main/
├── db/
│   ├── db.py              # Conexión y motor de BD
│   ├── session.py         # Sesión async
│   └── base.py            # Configuración base
├── models/
│   ├── entities.py        # Modelos SQLAlchemy
│   ├── models.py          # Esquemas comunes
│   └── schemas.py         # Pydantic schemas
├── routers/               # Blueprints de FastAPI
│   ├── subjects.py        # CRUD sujetos
│   ├── sleep_records.py   # CRUD registros
│   ├── sleep_stages.py    # Etapas del sueño
│   ├── lifestyle_factors.py # Factores estilo de vida
│   ├── tags.py            # Etiquetas
│   ├── uploads.py         # Supabase Storage
│   └── reports.py         # Reportes y CSV
├── templates/             # Jinja2 templates
│   ├── base.html          # Layout base
│   ├── dashboard.html     # Panel principal
│   ├── subjects.html      # Tabla sujetos
│   ├── records.html       # Tabla registros
│   └── partials/          # Componentes HTMX
├── static/                # CSS, JS estáticos
├── main.py                # Punto de entrada FastAPI
├── seed_data.py           # Carga datos de prueba
├── requirements.txt       # Dependencias
├── .env.example           # Variables de entorno
└── README.md
```

---

## Testing Manual

### Checklist de funcionalidades

- [ ] **Crear Sujeto** desde HTML `/subjects` y vía POST `/api/subjects`
- [ ] **Crear Registro** desde HTML `/records` con validación de `wakeup_time > bedtime`
- [ ] **Filtrar Registros** por fecha, género y sujeto
- [ ] **Adjuntar Archivo** a registro (POST `/api/uploads` + PATCH attach)
- [ ] **Exportar CSV** desde botones en `/subjects` y `/records`
- [ ] **Ver Dashboard** con gráficas cargadas y datos actualizados
- [ ] **Soft-delete** sujeto y verificar que registros asociados se mantienen
- [ ] **Restaurar** sujeto/registro desde API
- [ ] **Búsqueda por tag** en sujetos usando parámetro `q`
- [ ] **Reportes JSON** en `/api/reports/aggregates` y `/api/reports/timeseries`

---

## Reportes Disponibles

### Dashboard
- **Gráfica de Serie:** Duración de sueño en el tiempo
- **Gráfica de Barras:** Eficiencia por género
- **Gráfica Doughnut:** Distribución de etapas (o tags)

### API JSON
- **Agregados:** Promedio, mín, máx, desv. estándar por grupo
- **Series de Tiempo:** Datos diarios para gráficas
- **Distribuciones:** Conteos por categoría

### Exportación
- **CSV Subjects:** Nombre, edad, género, etiquetas
- **CSV Records:** Sujeto, fecha, duración, eficiencia, despertares

---

## Desarrollo

### Agregar un nuevo endpoint

```python
# routers/mi_router.py
from fastapi import APIRouter, Depends
from db.session import get_db

router = APIRouter()

@router.get("/mi-endpoint")
async def mi_endpoint(session=Depends(get_db)):
    # Tu lógica aquí
    return {"mensaje": "OK"}
```

Luego registrarlo en `main.py`:
```python
from routers.mi_router import router as mi_router
app.include_router(mi_router, prefix="/api")
```



## Dudas?

angel.ortiz102878@gmail.com
