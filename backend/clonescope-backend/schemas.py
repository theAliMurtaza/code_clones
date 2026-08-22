"""
schemas.py
Pydantic v2 schemas for all API request and response bodies.
"""

from __future__ import annotations
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    name:  str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      UUID
    name:         str
    email:        str


# ── Code line (for CodeViewer) ───────────────────────────────────────
class CodeLine(BaseModel):
    n:    int    # line number
    text: str    # line content


# ── Clone pair ───────────────────────────────────────────────────────
class ClonePairSchema(BaseModel):
    id:             UUID
    file_a:         str
    file_b:         str
    lines_a:        list[int]          # [start, end]
    lines_b:        list[int]
    clone_lines_a:  list[int]          # full list of highlighted lines
    clone_lines_b:  list[int]
    clone_type:     str                # "Type-1" … "Type-4"
    similarity:     float
    token_sim:      Optional[float]
    cross_language: bool
    description:    Optional[str]
    code_a:         str                # raw code snippet
    code_b:         str
    # Parsed lines for CodeViewer component
    code_lines_a:   list[CodeLine]
    code_lines_b:   list[CodeLine]

    class Config:
        from_attributes = True


# ── Job ───────────────────────────────────────────────────────────────
class JobSummary(BaseModel):
    id:              UUID
    status:          str
    created_at:      datetime
    completed_at:    Optional[datetime]
    total_fragments: int
    total_pairs:     int
    type1_count:     int
    type2_count:     int
    type3_count:     int
    type4_count:     int
    runtime_seconds: Optional[float]
    threshold:       float
    error:           Optional[str]

    class Config:
        from_attributes = True


class JobDetail(JobSummary):
    clone_pairs: list[ClonePairSchema]

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    id:          UUID
    status:      str
    created_at:  datetime
    total_pairs: int
    files:       list[str]   # filenames

    class Config:
        from_attributes = True


# ── Detect request (submitted as multipart form) ──────────────────────
class DetectConfig(BaseModel):
    threshold:     float = Field(0.75, ge=0.5, le=0.99)
    cross_language: bool = True


# ── Submit response ───────────────────────────────────────────────────
class SubmitResponse(BaseModel):
    job_id:  UUID
    status:  str
    message: str


# ── Stats (dashboard) ─────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_jobs:       int
    total_pairs:      int
    total_fragments:  int
    avg_f1:           Optional[float]
    type_distribution: dict[str, int]
