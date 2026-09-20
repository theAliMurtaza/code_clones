"""
config.py  —  All settings loaded from environment variables / .env file
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME:       str  = "CloneScope API"
    APP_VERSION:    str  = "1.0.0"
    DEBUG:          bool = False
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://clonescope:clonescope@localhost:5432/clonescope"

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL:           str = "redis://localhost:6379/0"
    EMBEDDING_CACHE_TTL: int = 86400

    # ── Celery ───────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_URL: str = "redis://localhost:6379/2"

    # ── Auth ─────────────────────────────────────────────────────────
    SECRET_KEY:                  str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── ML model ─────────────────────────────────────────────────────
    CODEBERT_MODEL:   str  = "microsoft/graphcodebert-base"
    # "auto" selects the low-memory lexical engine on Render and GraphCodeBERT
    # elsewhere. Set to "full" only on an instance with at least 2 GB RAM.
    DETECTION_ENGINE: str  = "auto"
    USE_GPU:          bool = False
    MODEL_CACHE_DIR:  str  = "./model_cache"
    # GraphCodeBERT attention uses substantial memory on CPU. Keep batches small
    # unless the deployment has been sized and tested for a larger value.
    BATCH_SIZE:       int  = 1
    MAX_TOKEN_LENGTH: int  = 512

    # ── Detection thresholds ─────────────────────────────────────────
    # DEFAULT_THRESHOLD: minimum cosine similarity (embedding mode) or
    #   P(clone) (classifier mode) to flag a pair.
    DEFAULT_THRESHOLD: float = 0.50

    TYPE1_TOKEN_SIM:   float = 0.95   # token sim for Type-1 (exact copy)
    TYPE2_SEM_SIM:     float = 0.75   # semantic sim for Type-2
    TYPE2_TOK_SIM:     float = 0.60   # token sim for Type-2 (renamed identifiers)
    TYPE3_SEM_SIM:     float = 0.65   # semantic sim for Type-3
    TYPE3_TOK_SIM:     float = 0.30   # token sim lower-bound for Type-3 (near-miss syntactic)
    TYPE4_SEM_SIM:     float = 0.50   # semantic sim for Type-4 (pure semantic clone)

    # ── File handling ─────────────────────────────────────────────────
    MAX_FILE_SIZE_MB:    int = 10
    MAX_FRAGMENTS_PER_JOB: int = 80
    SUPPORTED_EXTS:      str = ".py,.java"
    CODE_RETENTION_DAYS: int = 30

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def supported_extensions(self) -> list[str]:
        return [e.strip() for e in self.SUPPORTED_EXTS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
