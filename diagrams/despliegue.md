```mermaid
flowchart LR
    U["Usuario<br/>Navegador web"] -->|HTTPS| R["Render.com<br/>Servicio web"]

    subgraph Render
        R --> A["Aplicación SleepHabits<br/>FastAPI + Jinja + Chart.js"]
    end

    A -->|"TLS (postgresql+asyncpg)"| DB[("Supabase<br/>PostgreSQL")]
    A -->|"HTTP API"| ST[("Supabase Storage<br/>Bucket sleep-uploads")]

    class U client
    class R,A app
    class DB,ST storage
