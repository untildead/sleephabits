flowchart LR
    subgraph Usuario
        BROWSER[🧑‍💻 Navegador web\n(Chrome/Edge)]
    end

    subgraph Render["Render.com (Producción)"]
        subgraph App["Servicio web FastAPI"]
            GUNICORN[gunicorn\n+ uvicorn workers]
            API[main.py\nRouters FastAPI\nTemplates Jinja2\nChart.js]
        end
    end

    subgraph Supabase["Supabase (Cloud)"]
        DB[(PostgreSQL\nsleep_db)]
        STORAGE[(Storage\narchivos adjuntos)]
    end

    BROWSER <-- HTTP/HTTPS --> GUNICORN
    GUNICORN --> API
    API <-- TLS/Postgres --> DB
    API <-- HTTPS (SDK/API) --> STORAGE
