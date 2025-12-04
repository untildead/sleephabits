erDiagram
    SUBJECT {
        int id PK
        varchar name
        int age
        varchar gender
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    TAG {
        int id PK
        varchar name
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    SUBJECT_TAG {
        int id PK
        int subject_id FK
        int tag_id FK
    }

    SLEEP_RECORD {
        int id PK
        int subject_id FK
        date record_date
        timestamp bedtime
        timestamp wakeup_time
        numeric sleep_duration
        numeric sleep_efficiency
        int awakenings
        varchar attachment_url
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    SLEEP_STAGE {
        int id PK
        int sleep_record_id FK
        numeric rem_percentage
        numeric deep_percentage
        numeric light_percentage
    }

    LIFESTYLE_FACTORS {
        int id PK
        int sleep_record_id FK
        boolean caffeine_late
        boolean screen_before_bed
        boolean exercise
    }

    SUBJECT ||--o{ SLEEP_RECORD : "tiene"
    SUBJECT ||--o{ SUBJECT_TAG : "tiene"
    TAG ||--o{ SUBJECT_TAG : "etiqueta"
    SLEEP_RECORD ||--o| SLEEP_STAGE : "detalle etapas"
    SLEEP_RECORD ||--o| LIFESTYLE_FACTORS : "factores"
