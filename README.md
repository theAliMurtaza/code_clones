# CloneScope

CloneScope is a GraphCodeBERT-powered code-clone detection application.

## Repository layout

```text
code_clone_detector/
├── frontend/   React + Vite application
├── backend/    FastAPI detection API and GraphCodeBERT engine
└── README.md
```

## Run locally

Start the API from `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then start the client from `frontend`:

```powershell
npm install
npm run dev
```

## Folder analysis

Select or drop a folder to include `.py` and `.java` files recursively, including
hidden and build subdirectories. Other file types are skipped. Relative paths
identify files, so `src/main.py` and `tests/main.py` remain separate. Local path
scanning reads a directory on the API server.

All eligible fragments are compared across different files. Functions, short
scripts, and code outside functions are included; long units use overlapping
80-line blocks. Exact and renamed clones use token comparisons that preserve
operators and Python block structure. Near-miss matches require at least 75%
structural/token similarity and the selected threshold. Type-4 semantic matches
require a fine-tuned classifier; base embeddings alone do not establish equivalent
behavior. These heuristics are not an accuracy guarantee.

Results show both paths, original line numbers, and matching code side by side.
**View full code** opens the saved source, including for files with no matches.
Existing analyses must be rerun to use the updated detection logic.

The default limits are 10 MB per source file and 200 extracted fragments per job.
An oversized or unreadable input fails explicitly rather than producing partial
results. Configure `MAX_FILE_SIZE_MB` and `MAX_FRAGMENTS_PER_JOB` for your deployment.

Regression tests (from `backend`, with dependencies installed):

```powershell
python -m unittest test_folder_detection -v
```
