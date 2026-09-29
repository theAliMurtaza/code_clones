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
structural/token similarity and the selected threshold.

Type-4 semantic analysis uses the real GraphCodeBERT model even without fine-tuned
weights. Every pair other than exact/renamed clones is checked without a lexical
pre-filter. With the base model, Type-4 **candidates** require cosine similarity
of at least `max(selected threshold, TYPE4_EMBEDDING_SIM)` (default 0.85). This is
an uncalibrated heuristic, not a probability or proof of equivalent behavior.
Fine-tuned weights at `backend/saved_models/model.bin` enable pairwise classifier
scoring instead, with `TYPE4_SEM_SIM` (default 0.50) as its minimum cutoff.
Types 1–3 are retained; Type-4 results appear first.

The result page records the model mode, semantic comparisons performed, and
cutoff used. If only the lightweight structural engine is available, it explicitly
says Type-4 was **not checked**. Use `DETECTION_ENGINE=full` on a host with enough
memory (at least 2 GB) and installed PyTorch/Transformers to enable the real model.
Restart the backend after changing model configuration or adding trained weights.
Tune thresholds and measure precision/recall on representative labeled Type-4
positives and hard negatives; these heuristics are not an accuracy guarantee.

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

Optional real-model smoke check (requires downloaded model weights):

```powershell
$env:RUN_MODEL_TESTS='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
python -m unittest test_type4_model -v
```

This checks recursive/iterative factorial and Python/Java quicksort as Type-4
candidates, preserves a renamed Type-2 match, and rejects an unrelated greeting
function. It is a small integration fixture, not a representative accuracy benchmark.
For task-specific fine-tuning and evaluation, see
[Microsoft's clone-detection workflow](https://github.com/microsoft/CodeBERT/tree/master/GraphCodeBERT/clonedetection).
