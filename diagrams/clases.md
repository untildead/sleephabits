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

    class Tag {
        +int id
        +string name
        +bool is_deleted
        +datetime created_at
        +datetime updated_at
    }

    class SubjectTag {
        +int id
        +int subject_id
        +int tag_id
    }

    class SleepRecord {
        +int id
        +int subject_id
        +date record_date
        +datetime bedtime
        +datetime wakeup_time
        +float sleep_duration  // horas
        +float sleep_efficiency // %
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
    }

    class LifestyleFactors {
        +int id
        +int sleep_record_id
        +bool caffeine_late
        +bool screen_before_bed
        +bool exercise
    }

    Subject "1" --> "many" SleepRecord : registra
    Subject "1" --> "many" SubjectTag : tiene
    Tag "1" --> "many" SubjectTag : etiqueta
    SleepRecord "1" --> "0..1" SleepStage : detalleEtapas
    SleepRecord "1" --> "0..1" LifestyleFactors : factores