from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from db.base import Base


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (CheckConstraint("age >= 0", name="chk_subject_age"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    records = relationship("SleepRecord", back_populates="subject", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="subject_tags", back_populates="subjects")


class SleepRecord(Base):
    __tablename__ = "sleep_records"
    __table_args__ = (
        Index("idx_sleep_records_subject_date", "subject_id", "record_date"),
        CheckConstraint("sleep_duration > 0 AND sleep_duration <= 24", name="chk_sleep_duration"),
        CheckConstraint("sleep_efficiency >= 0 AND sleep_efficiency <= 100", name="chk_sleep_efficiency"),
    )

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    bedtime = Column(DateTime, nullable=False)
    wakeup_time = Column(DateTime, nullable=False)
    sleep_duration = Column(Float, nullable=False)
    sleep_efficiency = Column(Float, nullable=False)
    awakenings = Column(Integer, nullable=False, default=0)
    attachment_url = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subject = relationship("Subject", back_populates="records")
    stage = relationship("SleepStage", back_populates="record", uselist=False, cascade="all, delete-orphan")
    lifestyle = relationship("LifestyleFactors", back_populates="record", uselist=False, cascade="all, delete-orphan")


class SleepStage(Base):
    __tablename__ = "sleep_stages"
    __table_args__ = (UniqueConstraint("sleep_record_id", name="uq_stage_record"),)

    id = Column(Integer, primary_key=True, index=True)
    sleep_record_id = Column(Integer, ForeignKey("sleep_records.id", ondelete="CASCADE"), nullable=False)
    rem_percentage = Column(Float, nullable=False)
    deep_percentage = Column(Float, nullable=False)
    light_percentage = Column(Float, nullable=False)

    record = relationship("SleepRecord", back_populates="stage")


class LifestyleFactors(Base):
    __tablename__ = "lifestyle_factors"
    __table_args__ = (UniqueConstraint("sleep_record_id", name="uq_lifestyle_record"),)

    id = Column(Integer, primary_key=True, index=True)
    sleep_record_id = Column(Integer, ForeignKey("sleep_records.id", ondelete="CASCADE"), nullable=False)
    caffeine_consumption = Column(String, nullable=False)
    alcohol_consumption = Column(String, nullable=False)
    smoking_status = Column(String, nullable=False)
    exercise_frequency = Column(String, nullable=False)

    record = relationship("SleepRecord", back_populates="lifestyle")


class SubjectTag(Base):
    __tablename__ = "subject_tags"
    __table_args__ = (UniqueConstraint("subject_id", "tag_id", name="uq_subject_tag"),)

    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    subjects = relationship("Subject", secondary="subject_tags", back_populates="tags")
