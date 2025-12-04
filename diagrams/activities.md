flowchart TD
    A[Usuario abre /records/new] --> B[Completa formulario de registro de sueño]
    B --> C[Envía formulario (POST)]
    C --> D[Validar datos en backend\n- Nombre sujeto obligatorio\n- Género ∈ {F,M,O}\n- Fechas coherentes\n- Duración y eficiencia > 0]
    D -->|Error de validación| E[Devolver formulario con mensajes de error]
    E --> B

    D -->|Datos válidos| F[Buscar o crear Subject]
    F --> G[Crear SleepRecord\n(subject_id, fechas, duración, eficiencia, despertares)]
    G --> H[Asociar tags/hábitos (SubjectTag)]
    H --> I[Guardar en Supabase (PostgreSQL)]
    I --> J[Redirigir a listado /records]
    J --> K[Usuario puede ir a /dashboard]
    K --> L[Dashboard consulta\n/api/reports/timeseries\n/api/reports/habits_quality]
    L --> M[Mostrar gráficos\n- Promedio diario de sueño\n- Hábitos y calidad]
