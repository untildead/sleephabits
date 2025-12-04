from datetime import date, datetime, time, timedelta
from typing import List, Optional

import re
from pydantic import BaseModel, Field, field_validator, model_validator


NAME_RE = re.compile("^[A-Za-z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1' -]{2,50}$")


def ensure_sleep_window(record_date: date, bedtime: time, wakeup_time: time) -> tuple[datetime, datetime]:
    """Return bedtime/wakeup as datetimes, rolling wakeup to the next day if needed."""
    bed_dt = datetime.combine(record_date, bedtime)
    wake_dt = datetime.combine(record_date, wakeup_time)
    if wake_dt <= bed_dt:
        wake_dt += timedelta(days=1)
    return bed_dt, wake_dt


def compute_sleep_metrics(record_date: date, bedtime: time, wakeup_time: time, awakenings: int = 0) -> tuple[float, float]:
    """Calculate duration (hours) and efficiency (%) based on provided times."""
    bed_dt, wake_dt = ensure_sleep_window(record_date, bedtime, wakeup_time)
    time_in_bed_min = int((wake_dt - bed_dt).total_seconds() / 60)
    duration_hours = round(time_in_bed_min / 60, 2) if time_in_bed_min else 0.0
    awakenings = max(0, awakenings or 0)
    waso = awakenings * 5
    if time_in_bed_min == 0:
        efficiency = 0.0
    else:
        efficiency = round(max(0.0, min(100.0, 100 * (time_in_bed_min - waso) / time_in_bed_min)), 2)
    return duration_hours, efficiency


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int

    class Config:
        from_attributes = True


class SubjectBase(BaseModel):
    name: str = Field(..., description="2-50 letras")
    age: int = Field(..., ge=0, le=120)
    gender: str = Field(..., description="M/F/O")

    @field_validator("name")
    @classmethod
    def v_name(cls, v: str) -> str:
        cleaned = " ".join((v or "").strip().split())
        if not NAME_RE.match(cleaned):
            raise ValueError("El nombre solo puede contener letras y espacios (2-50 caracteres).")
        return cleaned

    @field_validator("age")
    @classmethod
    def v_age(cls, v: int) -> int:
        if v is None or not (0 <= v <= 120):
            raise ValueError("Edad inv\u00e1lida. Debe estar entre 0 y 120.")
        return v

    @field_validator("gender")
    @classmethod
    def v_gender(cls, v: str) -> str:
        cleaned = (v or "").strip().upper()
        if cleaned not in {"M", "F", "O"}:
            raise ValueError("G\u00e9nero inv\u00e1lido. Use M, F u O.")
        return cleaned


class SubjectCreate(SubjectBase):
    tag_ids: List[int] = Field(default_factory=list)


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    is_deleted: Optional[bool] = None
    tag_ids: Optional[List[int]] = None

    @field_validator("name")
    @classmethod
    def v_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = " ".join(v.strip().split())
        if not NAME_RE.match(cleaned):
            raise ValueError("El nombre solo puede contener letras y espacios (2-50 caracteres).")
        return cleaned

    @field_validator("age")
    @classmethod
    def v_age(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not (0 <= v <= 120):
            raise ValueError("Edad inv\u00e1lida. Debe estar entre 0 y 120.")
        return v

    @field_validator("gender")
    @classmethod
    def v_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip().upper()
        if cleaned not in {"M", "F", "O"}:
            raise ValueError("G\u00e9nero inv\u00e1lido. Use M, F u O.")
        return cleaned


class SubjectSummary(BaseModel):
    id: int
    name: Optional[str] = None
    age: int
    gender: str

    class Config:
        from_attributes = True


class SubjectRead(SubjectSummary):
    is_deleted: bool
    tags: List[TagRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SleepRecordBase(BaseModel):
    subject_id: int
    record_date: date
    bedtime: time
    wakeup_time: time
    sleep_duration: Optional[float] = None
    sleep_efficiency: Optional[float] = None
    awakenings: int = Field(0, ge=0, le=20)
    attachment_url: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("record_date")
    @classmethod
    def v_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha del registro no puede ser futura.")
        return v

    @field_validator("awakenings")
    @classmethod
    def v_awakenings(cls, v: int) -> int:
        if v is None:
            return 0
        if not (0 <= v <= 20):
            raise ValueError("El n\u00famero de despertares debe estar entre 0 y 20.")
        return v

    @field_validator("sleep_duration")
    @classmethod
    def v_duration(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (2.0 <= v <= 14.0):
            raise ValueError("La duraci\u00f3n del sue\u00f1o debe estar entre 2 y 14 horas.")
        return v

    @field_validator("sleep_efficiency")
    @classmethod
    def v_efficiency(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (0.0 <= v <= 100.0):
            raise ValueError("La eficiencia debe estar entre 0 y 100.")
        return round(v, 2)

    @model_validator(mode="after")
    def compute_and_validate_metrics(self):
        duration, efficiency = compute_sleep_metrics(
            self.record_date,
            self.bedtime,
            self.wakeup_time,
            self.awakenings,
        )
        if not (2.0 <= duration <= 14.0):
            raise ValueError("La duraci\u00f3n del sue\u00f1o debe estar entre 2 y 14 horas.")
        eff_value = self.sleep_efficiency if self.sleep_efficiency is not None else efficiency
        if not (0.0 <= eff_value <= 100.0):
            raise ValueError("La eficiencia debe estar entre 0 y 100.")
        self.sleep_duration = round(duration, 2)
        self.sleep_efficiency = round(eff_value, 2)
        return self


class SleepRecordCreate(SleepRecordBase):
    pass


class SleepRecordUpdate(BaseModel):
    subject_id: Optional[int] = None
    record_date: Optional[date] = None
    bedtime: Optional[time] = None
    wakeup_time: Optional[time] = None
    sleep_duration: Optional[float] = None
    sleep_efficiency: Optional[float] = None
    awakenings: Optional[int] = Field(default=None, ge=0, le=20)
    attachment_url: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: Optional[bool] = None

    @field_validator("record_date")
    @classmethod
    def v_date(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        if v > date.today():
            raise ValueError("La fecha del registro no puede ser futura.")
        return v

    @field_validator("awakenings")
    @classmethod
    def v_awakenings(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not (0 <= v <= 20):
            raise ValueError("El n\u00famero de despertares debe estar entre 0 y 20.")
        return v

    @field_validator("sleep_duration")
    @classmethod
    def v_duration(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (2.0 <= v <= 14.0):
            raise ValueError("La duraci\u00f3n del sue\u00f1o debe estar entre 2 y 14 horas.")
        return round(v, 2)

    @field_validator("sleep_efficiency")
    @classmethod
    def v_efficiency(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (0.0 <= v <= 100.0):
            raise ValueError("La eficiencia debe estar entre 0 y 100.")
        return round(v, 2)

    @model_validator(mode="after")
    def validate_and_compute(self):
        if self.record_date and self.bedtime and self.wakeup_time:
            duration, efficiency = compute_sleep_metrics(
                self.record_date,
                self.bedtime,
                self.wakeup_time,
                self.awakenings or 0,
            )
            self.sleep_duration = round(duration, 2)
            if self.sleep_efficiency is None:
                self.sleep_efficiency = round(efficiency, 2)
        if self.sleep_duration is not None and not (2.0 <= self.sleep_duration <= 14.0):
            raise ValueError("La duraci\u00f3n del sue\u00f1o debe estar entre 2 y 14 horas.")
        if self.sleep_efficiency is not None and not (0.0 <= self.sleep_efficiency <= 100.0):
            raise ValueError("La eficiencia debe estar entre 0 y 100.")
        return self


class SleepRecordRead(BaseModel):
    id: int
    subject_id: int
    record_date: date
    bedtime: datetime
    wakeup_time: datetime
    sleep_duration: float
    sleep_efficiency: float
    awakenings: int
    attachment_url: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: bool
    subject: Optional[SubjectSummary] = None

    class Config:
        from_attributes = True


class SleepStageBase(BaseModel):
    sleep_record_id: int
    rem_percentage: float
    deep_percentage: float
    light_percentage: float


class SleepStageCreate(SleepStageBase):
    pass


class SleepStageUpdate(BaseModel):
    sleep_record_id: Optional[int] = None
    rem_percentage: Optional[float] = None
    deep_percentage: Optional[float] = None
    light_percentage: Optional[float] = None


class SleepStageRead(SleepStageBase):
    id: int

    class Config:
        from_attributes = True


class LifestyleFactorsBase(BaseModel):
    sleep_record_id: int
    caffeine_consumption: str
    alcohol_consumption: str
    smoking_status: str
    exercise_frequency: str


class LifestyleFactorsCreate(LifestyleFactorsBase):
    pass


class LifestyleFactorsUpdate(BaseModel):
    sleep_record_id: Optional[int] = None
    caffeine_consumption: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    smoking_status: Optional[str] = None
    exercise_frequency: Optional[str] = None


class LifestyleFactorsRead(LifestyleFactorsBase):
    id: int

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    public_url: str
