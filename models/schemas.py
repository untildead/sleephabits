from datetime import date, datetime, time, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


def ensure_sleep_window(record_date: date, bedtime: time, wakeup_time: time) -> tuple[datetime, datetime]:
    """Return bedtime/wakeup as datetimes, rolling wakeup to the next day if needed."""
    bed_dt = datetime.combine(record_date, bedtime)
    wake_dt = datetime.combine(record_date, wakeup_time)
    if wake_dt <= bed_dt:
        wake_dt += timedelta(days=1)
    return bed_dt, wake_dt


def compute_sleep_metrics(
    record_date: date,
    bedtime: time,
    wakeup_time: time,
    awakenings: int = 0,
    sleep_latency_min: Optional[float] = None,
    waso_min: Optional[float] = None,
) -> tuple[float, float]:
    """Calculate duration (hours) and efficiency (%) based on provided times."""
    bed_dt, wake_dt = ensure_sleep_window(record_date, bedtime, wakeup_time)
    time_in_bed_min = int((wake_dt - bed_dt).total_seconds() / 60)
    duration_hours = round(time_in_bed_min / 60, 2) if time_in_bed_min else 0.0
    latency = sleep_latency_min or 0
    waso = waso_min if waso_min is not None else max(0, awakenings or 0) * 5
    if time_in_bed_min == 0:
        efficiency = 0
    else:
        efficiency = round(max(0, min(100, 100 * (time_in_bed_min - (latency + waso)) / time_in_bed_min)))
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
    name: Optional[str] = None
    age: int
    gender: str


class SubjectCreate(SubjectBase):
    tag_ids: List[int] = []


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    is_deleted: Optional[bool] = None
    tag_ids: Optional[List[int]] = None


class SubjectSummary(BaseModel):
    id: int
    name: Optional[str] = None
    age: int
    gender: str

    class Config:
        from_attributes = True


class SubjectRead(SubjectSummary):
    is_deleted: bool
    tags: List[TagRead] = []

    class Config:
        from_attributes = True


class SleepRecordBase(BaseModel):
    subject_id: int
    record_date: date
    bedtime: time
    wakeup_time: time
    sleep_duration: Optional[float] = None
    sleep_efficiency: Optional[float] = None
    awakenings: int = Field(0, ge=0)
    attachment_url: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def compute_and_validate_metrics(self):
        duration, efficiency = compute_sleep_metrics(
            self.record_date,
            self.bedtime,
            self.wakeup_time,
            self.awakenings,
            getattr(self, "sleep_latency_min", None),
            getattr(self, "waso_min", None),
        )
        if duration <= 0 or duration > 24:
            raise ValueError("sleep_duration must be between 0 and 24 hours")
        if efficiency < 0 or efficiency > 100:
            raise ValueError("sleep_efficiency must be between 0 and 100")
        self.sleep_duration = duration
        self.sleep_efficiency = efficiency
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
    awakenings: Optional[int] = Field(default=None, ge=0)
    attachment_url: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: Optional[bool] = None

    @model_validator(mode="after")
    def validate_and_compute(self):
        if self.record_date and self.bedtime and self.wakeup_time:
            duration, efficiency = compute_sleep_metrics(
                self.record_date,
                self.bedtime,
                self.wakeup_time,
                self.awakenings or 0,
                getattr(self, "sleep_latency_min", None),
                getattr(self, "waso_min", None),
            )
            self.sleep_duration = duration
            self.sleep_efficiency = efficiency
        if self.sleep_duration is not None and (self.sleep_duration <= 0 or self.sleep_duration > 24):
            raise ValueError("sleep_duration must be between 0 and 24 hours")
        if self.sleep_efficiency is not None and (self.sleep_efficiency < 0 or self.sleep_efficiency > 100):
            raise ValueError("sleep_efficiency must be between 0 and 100")
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
