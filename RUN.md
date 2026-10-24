# How to run NeuroRx

Commands are for PowerShell on Windows, run from the project root. They do not need `make`.
Output is a hypothesis for lab testing, not a treatment claim.

## Prerequisites

- Python 3.11 and Node 20 or newer.
- A `.env` file in the project root (it is gitignored). Copy `.env.example` and fill in `TINYFISH_API_KEY`, `NCBI_EMAIL`, `OLLAMA_HOST` and `OLLAMA_MODEL`.
  The pipeline needs these. The app does not.

## 1. Install (once)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
cd frontend; npm install; cd ..
```

## 2. Run the app

The repo already contains the data (`data/neurorx.db` and the exported JSON), so you can start here with no keys.

```powershell
.venv\Scripts\python scripts/dev.py
```

This starts the API on http://localhost:8000 and the UI on http://localhost:5173. Open the UI link. Press Ctrl-C to stop both.

UI only (falls back to the static data):

```powershell
cd frontend; npm run dev
```

## 3. Tests and lint (optional)

```powershell
.venv\Scripts\python -m pytest backend/tests -q
.venv\Scripts\python -m ruff check backend scripts
```

## 4. Re-run the pipeline (optional)

Needs the `.env` keys and the Ollama server.

```powershell
.venv\Scripts\python scripts/run_pipeline.py                  # everything
.venv\Scripts\python scripts/run_pipeline.py --stage ingest   # or: extract, agents
.venv\Scripts\python scripts/run_pipeline.py --stage build    # grade, validate, export JSON for the UI
```

It spends TinyFish calls. Search and Fetch are free-tier, and Agent runs are capped at 30 per process. Extraction is slow without a GPU model. Cached calls are reused, so a re-run costs little.

Related scripts:

```powershell
.venv\Scripts\python scripts/eval_extraction.py   # precision/recall against the gold set
.venv\Scripts\python scripts/slide_numbers.py     # regenerate results/slide_numbers.md
.venv\Scripts\python scripts/screenshots.py       # Playwright screenshots into results/screens
```

## 5. Build and deploy the static site

```powershell
cd frontend; npm run build; cd ..
npx vercel login
npx vercel --prod --yes
```

Run `vercel` from the repo root, because the Vercel project's root directory is set to `frontend`.

## Troubleshooting

- Port 8000 or 5173 already in use: stop whatever holds it before running `dev.py`. The launcher fails rather than picking another port.
- UI shows an error box: start the API with `dev.py`, or run `python scripts/run_pipeline.py --stage build` to regenerate `frontend/public/data/`.

Other docs: `README.md` (scoring method, limitations), `MVP.md` (scope, architecture, progress), `DEMO.md` (3-minute demo script).
