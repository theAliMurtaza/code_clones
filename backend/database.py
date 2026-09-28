"""
database.py
SQLAlchemy engine, session factory and Base class.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_settings

import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def _create_engine_with_fallback():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    try:
        eng = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        with eng.connect():
            pass
        return eng
    except Exception as exc:
        logger.warning(
            f"Could not connect to PostgreSQL ({exc}). Falling back to local SQLite database."
        )
        return create_engine("sqlite:///./clonescope.db", connect_args={"check_same_thread": False})

engine = _create_engine_with_fallback()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── Dependency for FastAPI routes ─────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
