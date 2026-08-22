"""
models.py
SQLAlchemy ORM models — User, Job, SourceFile, ClonePair.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Float, Integer,
    DateTime, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    QUEUED   = "queued"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"


# ── User ─────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    name            = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), default=utcnow)

    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


# ── Analysis Job ──────────────────────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status       = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    threshold    = Column(Float, default=0.75)
    error        = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Stats (populated after detection completes)
    total_fragments  = Column(Integer, default=0)
    total_pairs      = Column(Integer, default=0)
    type1_count      = Column(Integer, default=0)
    type2_count      = Column(Integer, default=0)
    type3_count      = Column(Integer, default=0)
    type4_count      = Column(Integer, default=0)
    runtime_seconds  = Column(Float, nullable=True)

    user        = relationship("User", back_populates="jobs")
    files       = relationship("SourceFile", back_populates="job", cascade="all, delete-orphan")
    clone_pairs = relationship("ClonePair", back_populates="job", cascade="all, delete-orphan")


# ── Source File (one per uploaded file) ──────────────────────────────
class SourceFile(Base):
    __tablename__ = "source_files"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id   = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    language = Column(String(50), nullable=False)   # "python" | "java"
    content  = Column(Text, nullable=False)
    size_kb  = Column(Float, nullable=True)

    job = relationship("Job", back_populates="files")


# ── Clone Pair (one per detected clone) ──────────────────────────────
class ClonePair(Base):
    __tablename__ = "clone_pairs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id        = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # File names
    file_a        = Column(String(500), nullable=False)
    file_b        = Column(String(500), nullable=False)

    # Line ranges [start, end]
    lines_a_start = Column(Integer, nullable=False)
    lines_a_end   = Column(Integer, nullable=False)
    lines_b_start = Column(Integer, nullable=False)
    lines_b_end   = Column(Integer, nullable=False)

    # Full list of highlighted line numbers (stored as JSON arrays)
    clone_lines_a = Column(JSON, nullable=False)   # e.g. [12, 13, 14, 15]
    clone_lines_b = Column(JSON, nullable=False)

    # Classification
    clone_type    = Column(String(10), nullable=False)   # "Type-1" … "Type-4"
    similarity    = Column(Float, nullable=False)
    token_sim     = Column(Float, nullable=True)
    cross_language= Column(Boolean, default=False)
    description   = Column(String(500), nullable=True)

    # Code snippets (stored for fast rendering — not for long-term storage)
    code_a        = Column(Text, nullable=False)
    code_b        = Column(Text, nullable=False)

    job = relationship("Job", back_populates="clone_pairs")
