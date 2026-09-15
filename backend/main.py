"""
main.py
FastAPI application — all routes, middleware, and startup events.

Routes:
  POST   /api/auth/register        Register a new user
  POST   /api/auth/login           Login and receive JWT
  GET    /api/me                   Current user profile

  POST   /api/detect               Upload files and start detection
  GET    /api/jobs                 List this user's jobs
  GET    /api/jobs/{job_id}        Full job detail + clone pairs
  DELETE /api/jobs/{job_id}        Delete a job (NFR-03-02)
  GET    /api/stats                Dashboard stats

  GET    /health                   Health check (for Docker / load balancer)
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile, File,
    Form, status, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import get_settings
from database import engine, get_db, Base
import models
import schemas
from auth import (
    hash_password, verify_password,
    create_access_token, get_current_user
)
from detector import run_detection, UploadedFile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger   = logging.getLogger(__name__)
settings = get_settings()

# ── App init ──────────────────────────────────────────────────────────
app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = "LLM-powered code clone detection using CodeBERT",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.allowed_origins_list,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Create DB tables on startup ───────────────────────────────────────
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")


# ── Health check ──────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# ═══════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/auth/register",
          response_model=schemas.TokenResponse,
          status_code=status.HTTP_201_CREATED,
          tags=["Auth"])
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """FR-08-01: Register with email + password."""
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    user = models.User(
        id              = uuid.uuid4(),
        email           = payload.email,
        name            = payload.name,
        hashed_password = hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return schemas.TokenResponse(
        access_token = token,
        user_id      = user.id,
        name         = user.name,
        email        = user.email,
    )


@app.post("/api/auth/login",
          response_model=schemas.TokenResponse,
          tags=["Auth"])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    """FR-08-01: Login and receive JWT."""
    user = db.query(models.User).filter(
        models.User.email == payload.email
    ).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    token = create_access_token(user.id, user.email)
    return schemas.TokenResponse(
        access_token = token,
        user_id      = user.id,
        name         = user.name,
        email        = user.email,
    )


@app.get("/api/me", tags=["Auth"])
def me(current_user: models.User = Depends(get_current_user)):
    return {
        "id":    str(current_user.id),
        "email": current_user.email,
        "name":  current_user.name,
    }


# ═══════════════════════════════════════════════════════════════════════
# DETECTION ROUTES
# ═══════════════════════════════════════════════════════════════════════

def _validate_file(f: UploadFile) -> None:
    """FR-01-02: Validate language and file size."""
    ext = "." + f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in settings.supported_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. "
                   f"Allowed: {settings.SUPPORTED_EXTS}"
        )


def _code_lines(code: str, start: int) -> list[schemas.CodeLine]:
    """Convert raw code string to CodeLine list for CodeViewer."""
    return [
        schemas.CodeLine(n=start + i, text=line)
        for i, line in enumerate(code.splitlines())
    ]


def _pair_to_schema(pair: models.ClonePair) -> schemas.ClonePairSchema:
    code_lines_a = _code_lines(pair.code_a, pair.lines_a_start)
    code_lines_b = _code_lines(pair.code_b, pair.lines_b_start)
    return schemas.ClonePairSchema(
        id             = pair.id,
        file_a         = pair.file_a,
        file_b         = pair.file_b,
        lines_a        = [pair.lines_a_start, pair.lines_a_end],
        lines_b        = [pair.lines_b_start, pair.lines_b_end],
        clone_lines_a  = pair.clone_lines_a,
        clone_lines_b  = pair.clone_lines_b,
        clone_type     = pair.clone_type,
        similarity     = pair.similarity,
        token_sim      = pair.token_sim,
        cross_language = pair.cross_language,
        description    = pair.description,
        code_a         = pair.code_a,
        code_b         = pair.code_b,
        code_lines_a   = code_lines_a,
        code_lines_b   = code_lines_b,
    )


@app.post("/api/detect",
          response_model=schemas.SubmitResponse,
          status_code=status.HTTP_202_ACCEPTED,
          tags=["Detection"])
async def detect(
    background_tasks: BackgroundTasks,
    files:     list[UploadFile] = File(...),
    threshold: float            = Form(default=settings.DEFAULT_THRESHOLD),
    db:        Session          = Depends(get_db),
    current_user: models.User   = Depends(get_current_user),
):
    """
    FR-01-01 + FR-05-02: Upload files and start async detection.
    Returns job_id immediately; poll GET /api/jobs/{job_id} for results.
    """
    # Validate all files before doing any work (FR-01-02)
    for f in files:
        _validate_file(f)
        if f.size and f.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"{f.filename} exceeds {settings.MAX_FILE_SIZE_MB} MB limit"
            )

    # ── Create Job record ─────────────────────────────────────────────
    job = models.Job(
        id        = uuid.uuid4(),
        user_id   = current_user.id,
        status    = models.JobStatus.QUEUED,
        threshold = max(0.3, min(0.99, threshold)),
    )
    db.add(job)

    # ── Read and store source files ───────────────────────────────────
    uploaded: list[UploadedFile] = []
    for f in files:
        content = (await f.read()).decode("utf-8", errors="replace")
        ext     = f.filename.rsplit(".", 1)[-1].lower()
        lang    = {"py": "python", "java": "java"}.get(ext, "unknown")
        db.add(models.SourceFile(
            id       = uuid.uuid4(),
            job_id   = job.id,
            filename = f.filename,
            language = lang,
            content  = content,
            size_kb  = round(len(content.encode()) / 1024, 2),
        ))
        uploaded.append(UploadedFile(filename=f.filename, content=content))

    db.commit()

    # ── Run detection as background task ──────────────────────────────
    # For small jobs: run inline in BackgroundTasks (no Celery needed)
    # For large jobs: dispatch to Celery worker
    # We use BackgroundTasks here so the server works without Celery.
    # To use Celery: replace background_tasks.add_task(...) with:
    #   from tasks import run_detection_job
    #   run_detection_job.delay(str(job.id))

    background_tasks.add_task(_run_job_inline, str(job.id), uploaded, job.threshold)

    return schemas.SubmitResponse(
        job_id  = job.id,
        status  = "queued",
        message = f"{len(files)} file(s) accepted. Poll /api/jobs/{job.id} for results.",
    )


def _run_job_inline(job_id: str, uploaded: list[UploadedFile], threshold: float):
    """
    Inline background runner (no Celery). Mirrors the Celery task logic.
    Swap for tasks.run_detection_job.delay(job_id) in production.
    """
    db = SessionLocal()  # new session for background thread
    try:
        _update_job_status(db, job_id, models.JobStatus.RUNNING)
        result = run_detection(uploaded, threshold=threshold)

        for pair in result.clone_pairs:
            db.add(models.ClonePair(
                id             = uuid.uuid4(),
                job_id         = job_id,
                file_a         = pair.file_a,
                file_b         = pair.file_b,
                lines_a_start  = pair.lines_a[0],
                lines_a_end    = pair.lines_a[1],
                lines_b_start  = pair.lines_b[0],
                lines_b_end    = pair.lines_b[1],
                clone_lines_a  = pair.clone_lines_a,
                clone_lines_b  = pair.clone_lines_b,
                clone_type     = pair.clone_type,
                similarity     = pair.similarity,
                token_sim      = pair.token_sim,
                cross_language = pair.cross_language,
                description    = pair.description,
                code_a         = pair.code_a,
                code_b         = pair.code_b,
            ))

        counts = {t: 0 for t in ["Type-1","Type-2","Type-3","Type-4"]}
        for p in result.clone_pairs:
            counts[p.clone_type] = counts.get(p.clone_type, 0) + 1

        db.query(models.Job).filter(models.Job.id == job_id).update({
            "status":          models.JobStatus.DONE,
            "completed_at":    datetime.now(timezone.utc),
            "total_fragments": result.total_fragments,
            "total_pairs":     len(result.clone_pairs),
            "type1_count":     counts["Type-1"],
            "type2_count":     counts["Type-2"],
            "type3_count":     counts["Type-3"],
            "type4_count":     counts["Type-4"],
            "runtime_seconds": result.runtime_seconds,
        })
        db.commit()

    except Exception as exc:
        logger.exception(f"Inline job {job_id} failed: {exc}")
        db.query(models.Job).filter(models.Job.id == job_id).update({
            "status":       models.JobStatus.FAILED,
            "completed_at": datetime.now(timezone.utc),
            "error":        str(exc)[:2000],
        })
        db.commit()
    finally:
        db.close()


def _update_job_status(db: Session, job_id: str, status: models.JobStatus):
    db.query(models.Job).filter(models.Job.id == job_id).update(
        {"status": status}
    )
    db.commit()


# Import SessionLocal here to avoid circular import at module level
from database import SessionLocal


# ═══════════════════════════════════════════════════════════════════════
# JOB QUERY ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/jobs",
         response_model=list[schemas.JobListItem],
         tags=["Jobs"])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """FR-08-02: List all analysis jobs for the current user."""
    jobs = (
        db.query(models.Job)
        .filter(models.Job.user_id == current_user.id)
        .order_by(models.Job.created_at.desc())
        .all()
    )
    result = []
    for job in jobs:
        result.append(schemas.JobListItem(
            id          = job.id,
            status      = job.status.value,
            created_at  = job.created_at,
            total_pairs = job.total_pairs,
            files       = [f.filename for f in job.files],
        ))
    return result


@app.get("/api/jobs/{job_id}",
         response_model=schemas.JobDetail,
         tags=["Jobs"])
def get_job(
    job_id: str,
    db:     Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """FR-09: Get full job results including all clone pairs."""
    job = (
        db.query(models.Job)
        .filter(
            models.Job.id      == job_id,
            models.Job.user_id == current_user.id,   # FR-08-03: isolation
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return schemas.JobDetail(
        id              = job.id,
        status          = job.status.value,
        created_at      = job.created_at,
        completed_at    = job.completed_at,
        total_fragments = job.total_fragments,
        total_pairs     = job.total_pairs,
        type1_count     = job.type1_count,
        type2_count     = job.type2_count,
        type3_count     = job.type3_count,
        type4_count     = job.type4_count,
        runtime_seconds = job.runtime_seconds,
        threshold       = job.threshold,
        error           = job.error,
        clone_pairs     = [_pair_to_schema(p) for p in job.clone_pairs],
    )


@app.delete("/api/jobs/{job_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["Jobs"])
def delete_job(
    job_id: str,
    db:     Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """NFR-03-02: Delete job, source files, and all generated data."""
    job = db.query(models.Job).filter(
        models.Job.id      == job_id,
        models.Job.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════
# STATS ROUTE
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/stats",
         response_model=schemas.DashboardStats,
         tags=["Stats"])
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """FR-07-01: Aggregated stats for the dashboard."""
    jobs = (
        db.query(models.Job)
        .filter(
            models.Job.user_id == current_user.id,
            models.Job.status  == models.JobStatus.DONE,
        )
        .all()
    )

    total_jobs      = len(jobs)
    total_pairs     = sum(j.total_pairs     for j in jobs)
    total_fragments = sum(j.total_fragments for j in jobs)

    distribution = {
        "Type-1": sum(j.type1_count for j in jobs),
        "Type-2": sum(j.type2_count for j in jobs),
        "Type-3": sum(j.type3_count for j in jobs),
        "Type-4": sum(j.type4_count for j in jobs),
    }

    return schemas.DashboardStats(
        total_jobs        = total_jobs,
        total_pairs       = total_pairs,
        total_fragments   = total_fragments,
        avg_f1            = None,   # computed offline in evaluation module
        type_distribution = distribution,
    )
