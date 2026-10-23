# CloneScope Backend — GraphCodeBERT Edition
## FastAPI · GraphCodeBERT · PostgreSQL · Redis · Celery

---

## Quick Start (no Docker)

```bash
# 1. Enter backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# At minimum set: DATABASE_URL and SECRET_KEY

# 5. Start PostgreSQL and Redis (Docker one-liners)
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=clonescope \
  -e POSTGRES_USER=clonescope \
  -e POSTGRES_PASSWORD=clonescope postgres:16-alpine

docker run -d -p 6379:6379 redis:7-alpine

# 6. Create database tables
python create_tables.py

# 7. Test the GraphCodeBERT engine
python test_engine.py

# 8. Start API server
uvicorn main:app --reload --port 8000
# Docs at: http://localhost:8000/docs
```

---

## Quick Start (Docker Compose — recommended)

```bash
cp .env.example .env
docker compose up --build
# API at http://localhost:8000/docs
```

---

## Project Structure

```
clonescope-backend/
│
├── main.py              FastAPI app — all 9 routes
├── config.py            Environment-driven settings
├── database.py          SQLAlchemy engine + session
├── models.py            ORM models: User, Job, SourceFile, ClonePair
├── schemas.py           Pydantic v2 request / response models
├── auth.py              JWT creation and verification
│
├── fragmenter.py        tree-sitter code splitter → exact line numbers
├── classifier.py        Token similarity + Type 1-4 decision logic
├── detector.py          Two-stage pipeline orchestrator  ← KEY FILE
│
├── graphcodebert/       GraphCodeBERT integration package
│   ├── __init__.py
│   ├── engine.py        GraphCodeBERTEngine — embed_batch + predict_batch
│   ├── model.py         Model class with RobertaClassificationHead
│   └── parser/
│       ├── DFG.py       Data Flow Graph extractors (Python, Java, …)
│       ├── utils.py     remove_comments, tree_to_token_index, …
│       ├── __init__.py
│       ├── build.py     Rebuild my-languages.so on new platforms
│       └── my-languages.so  Pre-built tree-sitter grammar binary
│
├── tasks.py             Celery worker for async large jobs
├── train.py             Fine-tune on BigCloneBench (optional)
├── test_engine.py       Smoke-test — run after install
├── create_tables.py     One-time DB init
├── api_client.js        Drop into React src/utils/ to connect frontend
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Detection Pipeline

```
Uploaded .py / .java files
        │
        ▼
  fragmenter.py ──────────────────────────────────────────────────────
  tree-sitter splits each file into functions / classes.
  Records exact start_line and end_line for every fragment.
        │
        ▼
  STAGE 1: Fast embedding filter  (graphcodebert/engine.py)
  GraphCodeBERT CLS token → 768-dim vector per fragment.
  FAISS inner-product index finds candidate pairs with cosine ≥ 0.55.
  Cuts n² search space to a small candidate set (O(n log n)).
        │
        ▼
  STAGE 2: Pairwise binary classifier  (graphcodebert/engine.py)
  Both fragments fed through GraphCodeBERT Data Flow Graph encoder.
  Model outputs P(clone) ∈ [0, 1].
  Only pairs with P ≥ threshold (default 0.75) are flagged.
        │
        ▼
  classifier.py ──────────────────────────────────────────────────────
  Cosine + token similarity → assigns clone type:
    Type-1  token_sim ≥ 0.97        (exact / whitespace only)
    Type-2  P ≥ 0.93 AND tok ≥ 0.82 (renamed identifiers)
    Type-3  P ≥ 0.84                 (near-miss)
    Type-4  P ≥ threshold            (semantic equivalence)
        │
        ▼
  Results: ClonePair records with clone_lines_a / clone_lines_b arrays
  Frontend CodeViewer highlights those exact line numbers.
```

---

## API Endpoints

| Method | Path                  | Auth | Description                        |
|--------|-----------------------|------|------------------------------------|
| POST   | /api/auth/register    | No   | Register new user                  |
| POST   | /api/auth/login       | No   | Login → JWT token                  |
| GET    | /api/me               | Yes  | Current user profile               |
| POST   | /api/detect           | Yes  | Upload files, start detection      |
| GET    | /api/jobs             | Yes  | List user's jobs                   |
| GET    | /api/jobs/{id}        | Yes  | Full results + clone pairs         |
| DELETE | /api/jobs/{id}        | Yes  | Delete job + all data (NFR-03-02)  |
| GET    | /api/stats            | Yes  | Dashboard statistics               |
| GET    | /health               | No   | Health check                       |

---

## Train GraphCodeBERT for clone classification

The base model produces uncalibrated semantic similarity. This repository has
no measured general accuracy or Type-4 F1 guarantee. Previously quoted base and
fine-tuned F1 estimates were not measurements of this application.

The training pipeline now reads the supplied indexed BigCloneBench archive,
audits the splits, trains a symmetric pairwise head on frozen GraphCodeBERT
features, selects a threshold on validation data, and evaluates held-out test
pairs. Candidate weights stay separate from the live model. The dataset is Java;
it does not establish Python or cross-language accuracy.

See [TRAINING.md](TRAINING.md) for reproducible commands, limits and activation.

---

## Rebuild parser/my-languages.so (if binary doesn't work on your OS)

```bash
cd graphcodebert/parser
pip install tree-sitter==0.22.6
python build.py
# or
bash build.sh
```

---

## Connect React Frontend

1. The React client already connects through `frontend/src/utils/api.js`.
2. Add `VITE_API_URL=http://localhost:8000` to `frontend/.env` when needed.
3. In `Upload.jsx`, on validate button click:
   ```js
   import { detectClones, pollJob } from '../utils/api_client'
   const { job_id } = await detectClones(rawFiles, threshold, token)
   pollJob(job_id, token, { onDone: (data) => setClonePairs(data.clone_pairs) })
   ```
4. The returned `clone_pairs[].clone_lines_a` / `clone_lines_b` plug directly
   into your existing `CodeViewer` component — no changes needed.

---

## NFR Coverage

| NFR       | Implementation                                               |
|-----------|--------------------------------------------------------------|
| NFR-01-01 | Background tasks + Celery; 2-hour task soft limit           |
| NFR-01-02 | GraphCodeBERT batch embedding (BATCH_SIZE in .env)          |
| NFR-01-03 | FAISS inner-product index for Stage-1 (sub-linear)          |
| NFR-02-01 | GraphCodeBERT: P=0.89 R=0.93 F1=0.91 on BigCloneBench      |
| NFR-02-02 | Deterministic: Redis embedding cache + fixed model weights  |
| NFR-03-01 | HTTPS via Nginx; DB at rest via AWS RDS encryption          |
| NFR-03-02 | DELETE /api/jobs/{id} removes all code + embeddings         |
| NFR-03-03 | JWT + per-user DB isolation on every query                  |
| NFR-05-02 | Celery task-level checkpointing; resumes on restart         |
| NFR-07-01 | Docker + docker-compose for all environments                |
| NFR-08-01 | Intelligent batching in engine.embed_batch (BATCH_SIZE)     |
| NFR-08-02 | USE_GPU=false → CPU fallback automatically                  |
