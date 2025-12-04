```mermaid
flowchart TD
    subgraph Frontend
        F1[/GET /dashboard/]
        F2[/GET /subjects/]
        F3[/GET /records/]
    end

    subgraph Backend_API
        E1[GET /api/reports/timeseries]
        E2[GET /api/reports/habits_quality]
        E3[GET /api/reports/subjects.csv]
        E4[GET /api/reports/records.csv]

        S1[GET /api/subjects]
        S2[POST /api/subjects]

        R1[GET /api/records]
        R2[POST /api/records]

        U1[POST /api/upload]
    end

    F1 --> E1
    F1 --> E2

    F2 --> S1
    F2 --> S2

    F3 --> R1
    F3 --> R2
    F2 --> E3
    F3 --> E4

    F3 --> U1
