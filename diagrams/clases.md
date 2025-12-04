# Diagramas del sistema SleepHabits


## 1. Diagrama de clases

```mermaid
classDiagram
    class Subject {
        +int id
        +string name
        +int age
        +string gender  // F, M, O
        +bool is_deleted
        +datetime created_at
        +datetime updated_at
    }

    class SleepRecord {
        +int id
        +int subject_id
        +date record_date
        +datetime bedtime
        +datetime wakeup_time
        +float sleep_duration  // horas
        +float sleep_efficiency  // 0-100
        +int awakenings
        +string attachment_url
        +bool is_deleted
        +datetime created_at
        +datetime updated_at
    }

    class SleepStage {
        +int id
        +int sleep_record_id
        +float rem_percentage
        +float deep_percentage
        +float light_percentage
        +datetime created_at
        +datetime updated_at
    }

    class Tag {
        +int id
        +string name
        +bool is_deleted
        +datetime created_at
        +datetime updated_at
    }

    class SubjectTag {
        +int subject_id
        +int tag_id
    }

    class LifestyleFactors {
        +int id
        +int sleep_record_id
        +int caffeine_late
        +int screens_late
        +int exercise
        +string notes
    }

    Subject "1" --> "many" SleepRecord : registra
    SleepRecord "1" --> "0..1" SleepStage : tiene
    SleepRecord "1" --> "0..1" LifestyleFactors : asocia
    Subject "1" --> "many" SubjectTag : etiqueta
    Tag "1" --> "many" SubjectTag : participa

...  
