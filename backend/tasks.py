"""
tasks.py
Celery worker tasks for async clone detection.

For large codebases the API submits a job and returns immediately.
The frontend polls GET /api/job/{id} until status == "done".
This satisfies NFR-05-02 (checkpointing) and FR-05-02 (async jobs).
"""

from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.orm import Session

from config import get_settings
import models
from database import SessionLocal
from detector import run_detection, UploadedFile

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── Celery app ────────────────────────────────────────────────────────
celery_app = Celery(
    "clonescope",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_URL,
)

celery_app.conf.update(
    task_serializer    = "json",
    result_serializer  = "json",
    accept_content     = ["json"],
    timezone           = "UTC",
    task_track_started = True,
    # Retry on soft time limit exceeded
    task_soft_time_limit = 3600,   # 1 hour
    task_time_limit      = 7200,   # 2 hours (NFR-01-01)
)


# ── Helper to update Job status in DB ────────────────────────────────
def _update_job(db: Session, job_id: str, **kwargs):
    db.query(models.Job).filter(
        models.Job.id == job_id
    ).update(kwargs)
    db.commit()


# ── Main Celery task ──────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_detection_job")
def run_detection_job(self, job_id: str):
    """
    Background task that runs the full detection pipeline for a job.
    Progress is written back to the DB so the frontend can poll for it.
    """
    db = SessionLocal()
    try:
        # ── Mark job as running ───────────────────────────────────────
        _update_job(db, job_id, status=models.JobStatus.RUNNING)

        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # ── Load source files ─────────────────────────────────────────
        uploaded = [
            UploadedFile(filename=f.filename, content=f.content)
            for f in job.files
        ]

        # ── Run pipeline ──────────────────────────────────────────────
        result = run_detection(uploaded, threshold=job.threshold)

        # ── Persist clone pairs ───────────────────────────────────────
        for pair in result.clone_pairs:
            db.add(models.ClonePair(
                id             = uuid.uuid4(),
                job_id         = job.id,
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

        # ── Update job stats ──────────────────────────────────────────
        type_counts = {"Type-1": 0, "Type-2": 0, "Type-3": 0, "Type-4": 0}
        for p in result.clone_pairs:
            type_counts[p.clone_type] = type_counts.get(p.clone_type, 0) + 1

        _update_job(db, job_id,
            status          = models.JobStatus.DONE,
            completed_at    = datetime.now(timezone.utc),
            total_fragments = result.total_fragments,
            total_pairs     = len(result.clone_pairs),
            type1_count     = type_counts["Type-1"],
            type2_count     = type_counts["Type-2"],
            type3_count     = type_counts["Type-3"],
            type4_count     = type_counts["Type-4"],
            runtime_seconds = result.runtime_seconds,
        )
        db.commit()
        logger.info(f"Job {job_id} completed: {len(result.clone_pairs)} pairs")

    except Exception as exc:
        logger.exception(f"Job {job_id} failed: {exc}")
        try:
            _update_job(db, job_id,
                status       = models.JobStatus.FAILED,
                completed_at = datetime.now(timezone.utc),
                error        = str(exc)[:2000],
            )
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
        import gc
        gc.collect()
