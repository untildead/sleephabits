```mermaid
    erDiagram
        SUBJECT {
            int id PK
            varchar name
            int age
            varchar gender
            bool is_deleted
            timestamp created_at
            timestamp updated_at
        }
    
        SLEEP_RECORD {
            int id PK
            int subject_id FK
            date record_date
            timestamp bedtime
            timestamp wakeup_time
            float sleep_duration
            float sleep_efficiency
            int awakenings
            varchar attachment_url
            bool is_deleted
            timestamp created_at
            timestamp updated_at
        }
    
        SLEEP_STAGE {
            int id PK
            int sleep_record_id FK
            float rem_percentage
            float deep_percentage
            float light_percentage
        }
    
        TAG {
            int id PK
            varchar name
            bool is_deleted
            timestamp created_at
            timestamp updated_at
        }
    
        SUBJECT_TAG {
            int subject_id FK
            int tag_id FK
        }
    
        LIFESTYLE_FACTORS {
            int id PK
            int sleep_record_id FK
            int caffeine_late
            int screens_late
            int exercise
            varchar notes
        }
    
        SUBJECT ||--o{ SLEEP_RECORD : "registra"
        SLEEP_RECORD ||--o| SLEEP_STAGE : "detalle etapas"
        SLEEP_RECORD ||--o| LIFESTYLE_FACTORS : "factores"
        SUBJECT ||--o{ SUBJECT_TAG : "tiene"
        TAG ||--o{ SUBJECT_TAG : "etiqueta"
