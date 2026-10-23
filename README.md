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

All eligible fragments are compared within each file and across different files.
Within a file, regions that overlap are excluded so a fragment cannot match its
own source lines. One analysis combines Types 1–3 structural matches with Type-4
semantic candidates when the local or remote model is available. Functions, short
scripts, and code outside functions are included; long units use overlapping
80-line blocks. Exact and renamed clones use token comparisons that preserve
operators and Python block structure. Near-miss matches require at least 75%
structural/token similarity and the selected threshold.

Type-4 semantic analysis uses GraphCodeBERT scores plus evidence checks. Base
embeddings alone cannot produce a result: candidates need diverse agreeing
bounded Python samples and the configured/user score threshold. Unsupported
semantic comparisons are withheld, so valid clones can be missed.

A separately trained pairwise head can score its evaluated language pairs using
a validation-selected threshold. Weights require matching evaluation metadata;
an unvalidated checkpoint cannot activate classifier mode. Observed behavioral
counterexamples always reject a candidate. See [training details](backend/TRAINING.md).
Neither route proves equivalence or promises 100% accuracy.
Types 1–3 are retained; Type-4 results appear first.

The result page records the model mode, semantic comparisons performed, and
cutoff used. If only the lightweight structural engine is available, it explicitly
says Type-4 was **not checked**. Use `DETECTION_ENGINE=full` on a host with enough
memory (at least 2 GB) and installed PyTorch/Transformers to enable the real model.
Restart the backend after changing model configuration or adding trained weights.
For Render Free, use `DETECTION_ENGINE=remote` with a separately hosted model:
see [the Oracle Always Free deployment guide](backend/deploy/README.md).
If Oracle has no capacity, use [your Windows laptop as the model server](backend/deploy/LAPTOP-SETUP.md).
The launcher supplies an authenticated temporary HTTPS endpoint for Render;
keep the laptop awake during analyses and update Render's URL after each restart.
For an eligible Hugging Face account, use [the ZeroGPU Space setup guide](backend/deploy/HUGGINGFACE-ZEROGPU.md)
to move model inference off the laptop and use a stable Gradio API URL.
Tune thresholds and measure precision/recall on representative labeled Type-4
positives and hard negatives; these heuristics are not an accuracy guarantee.

Results show both paths, original line numbers, and matching code side by side.
For a single-file and folder demonstration covering all four categories, see
[the all-types demo](examples/all-types-demo/README.md).
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
