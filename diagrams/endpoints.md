flowchart TD
    ROOT[/"/"/] --> R1[/"/records"/]
    ROOT --> S1[/"/subjects"/]
    ROOT --> D1[/"/dashboard"/]

    R1 --> R2[/GET /records/new/]
    R1 --> R3[/POST /records/new/]
    R1 --> R4[/GET /records/{id}/edit/]
    R1 --> R5[/POST /records/{id}/edit/]
    R1 --> R6[/POST /records/{id}/delete/]

    S1 --> S2[/GET /subjects/new/]
    S1 --> S3[/POST /subjects/new/]
    S1 --> S4[/GET /subjects/{id}/edit/]
    S1 --> S5[/POST /subjects/{id}/edit/]
    S1 --> S6[/POST /subjects/{id}/delete/]

    subgraph API_Reports["/api/reports/*"]
        T1[/GET /api/reports/timeseries/]
        T2[/GET /api/reports/habits_quality/]
        T3[/GET /api/reports/aggregates/]
        T4[/GET /api/reports/distribution/]
        T5[/GET /api/reports/records.csv/]
        T6[/GET /api/reports/subjects.csv/]
    end

    D1 --> T1
    D1 --> T2
