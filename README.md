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
