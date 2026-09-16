# ── CloneScope Backend Dockerfile ───────────────────────────────────
# Multi-stage build: smaller final image without build tools.
# NFR-07-01: Containerised with all dependencies.

# ── Stage 1: builder ─────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed for psycopg2 and tree-sitter compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create non-root user (NFR-03-03: security)
RUN addgroup --system app && adduser --system --ingroup app app
RUN chown -R app:app /app
USER app

# Create model cache directory
RUN mkdir -p /app/model_cache

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health')"

# Start server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
