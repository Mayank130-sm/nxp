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

The repo includes `data/neurorx.db`, so after the install in step 1 `dev.py` works on a fresh clone with no keys. The UI-only command below needs no database at all and reads the exported JSON in `frontend/public/data/`.

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

## How the database works

The database is a single SQLite file, `data/neurorx.db`. The code is in `backend/app/db.py`, and the path is set by `DB_PATH` in `backend/app/config.py`. It is committed to the repo (about 1.6 MB), so a fresh clone can run the API straight away. Only the database is committed: the paper text files it points to (`text_path`), the TinyFish cache and backup copies are not, so re-running extraction on the same papers means re-running ingest first. Commit it again after you re-run the pipeline (and run `PRAGMA wal_checkpoint(TRUNCATE)` first so the file is complete).

| Table | Holds |
|---|---|
| `papers` | One row per paper: PMID, DOI, title, year, source URL, `fulltext_available`, and `text_path` (the paper text is stored as a file, not in the database) |
| `paper_drugs` | Which seed drugs each paper mentions |
| `claims` | Extracted claims: drug, stage, direction, species, study design, markers, dose, pathways, the verbatim `evidence_quote`, `quote_verified` |
| `claim_scores` | The 0-100 `confidence` per claim, with the replication, design, markers, species and dose parts and any `penalties` |
| `trials` | ClinicalTrials.gov rows from the Agent (drug, NCT id, phase, status, condition) |
| `drug_notes` | Drug-label notes from the Agent (blood-brain-barrier and safety notes) |
| `extract_stats` | Counters per paper and drug: windows, gate passes, proposed, quote failed, kept |
| `checkpoints` | Which stages and keys are finished, so a re-run skips them |

How data flows through it:

1. `ingest.py` writes `papers` and `paper_drugs`. It merges duplicates by PMID, then DOI, then a title key.
2. `extract.py` writes `claims`. Only claims whose quote matches the paper text exactly get `quote_verified=1`.
3. `grade.py` reads `claims`, writes `claim_scores` and detects conflicts.
4. `rank.py` and `graph.py` read the graded claims and build the ranking and `data/graph.json`.
5. `service.py` and `main.py` (FastAPI) serve it. `scripts/export_static.py` dumps the same data to `frontend/public/data/*.json` for the hosted site.

The connection uses a 60-second timeout, because an Agent job once crashed with "database is locked". The `checkpoints` table is what makes the pipeline resumable.

## Get more papers (flags)

`run_pipeline.py` takes the paper counts as flags, so you do not need to edit code:

```powershell
# more papers for every drug, re-doing ingest for them (back up data
eurorx.db first)
.venv\Scripts\python scripts/run_pipeline.py --stage ingest --reingest --pubmed-n 40 --fulltext-n 10
.venv\Scripts\python scripts/run_pipeline.py --stage extract    # only the new papers are read
.venv\Scripts\python scripts/run_pipeline.py --stage build
```

- `--pubmed-n` is PubMed papers per drug (default 14). `--fulltext-n` is full-text fetches per drug (default 4).
- `--reingest` clears the ingest checkpoints for the selected drugs. Without it, finished drugs are skipped.
- `--drugs a,b` limits any stage to those drugs.
- Papers are merged by PMID, DOI and title, so re-ingesting does not create duplicates.
- Set `TINYFISH_TIMEOUT=400` (seconds) in the environment if Agent runs time out. The default is 150.

## Human labels for the gold set

```powershell
.venv\Scripts\python scripts/make_human_sheet.py                       # writes data\labels\gold_human_blank.csv, sentences only
# a person fills has_claim (1/0) and the other columns, then saves it as data\labels\gold_human.csv
.venv\Scripts\python scripts/make_human_sheet.py --compare data\labels\gold_human.csv   # agreement with the AI labels (Cohen kappa)
.venv\Scripts\python scripts/eval_extraction.py --gold data\labels\gold_human.csv --out results\extraction_eval.json
.venv\Scripts\python scripts/run_pipeline.py --stage build
```

The blank sheet has no AI labels, so the annotator is not anchored by them. The labelling rule and the allowed values are in the header of `scripts/make_human_sheet.py`. Until a human file exists, the extraction numbers stay labelled as AI-made.

## Query the database

The database is a normal SQLite file, so any SQLite tool works. Python is already in your virtualenv:

```powershell
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('data/neurorx.db'); print(c.execute('select drug, count(*) from claims where quote_verified=1 group by drug order by 2 desc limit 5').fetchall())"
```

For an interactive prompt, use the `sqlite3` command-line tool if you have it (`sqlite3 data/neurorx.db`), or a viewer such as DB Browser for SQLite. Open the file read-only if the pipeline might be running, because writes lock it.

Useful queries:

```sql
-- verified claims for one drug, with their quotes
select direction, stage, species, evidence_quote from claims where drug='fluoxetine' and quote_verified=1;

-- strongest scored claims
select c.drug, c.direction, s.confidence, c.evidence_quote
from claims c join claim_scores s on s.claim_id=c.id
order by s.confidence desc limit 10;

-- papers behind a drug
select p.pmid, p.title, p.year from papers p join paper_drugs d on d.paper_id=p.id where d.drug='lithium';

-- trials the Agent found
select drug, nct_id, phase, status from trials order by drug;

-- see every table's columns
select name from sqlite_master where type='table';
```

Do not edit `claims` or `claim_scores` by hand. `claim_scores` is rebuilt by `run_pipeline.py --stage build`, which overwrites manual changes.

## How TinyFish works and where it is used

The client is `backend/app/tinyfish_client.py`. The TinyFish URLs, rate limits and the Agent cap (`AGENT_RUN_CAP`, 30 per process) are in `backend/app/config.py`. The API key is read from `.env` and sent in an `X-API-Key` header.

| Call | Used in | What it does |
|---|---|---|
| `search()` | `backend/app/ingest.py` | For each drug, finds ranked open-access paper URLs |
| `fetch()` | `backend/app/ingest.py` | Fetches up to 10 URLs at a time as Markdown. `ingest.py` then keeps the Methods and Results sections |
| `run_agent()` | `backend/app/agents.py` | Drives ClinicalTrials.gov for trial lists and DailyMed for label notes. These sites have no API |

What the client adds around each call:

- **Cache:** `_cached` stores responses on disk, keyed by a hash of the endpoint and parameters. Repeat calls cost nothing.
- **Rate limiting:** a token bucket keeps it within TinyFish's limits.
- **Retries:** `_request` retries with backoff.
- **Agent cap:** it raises `AgentCapReached` once the cap is hit.
- **Dry-run mode:** it can run without making live calls.
- **Call log:** every call is written to `data/tinyfish_calls.jsonl`. That is the source of the counts on the Methods page and in `stats.json` (search 85, fetch 29, agent 66 live calls).

PubMed does not go through TinyFish. `backend/app/pubmed.py` calls NCBI directly for the abstracts. TinyFish adds full text and the Agent lookups on top.

The logs under `data/` and the cache are gitignored. The database (`data/neurorx.db`) is committed, along with the exported JSON (`frontend/public/data/`, `data/graph.json`), the seed list and the gold labels. Backup copies (`data/*.backup*.db`) are ignored.

## Troubleshooting

- Port 8000 or 5173 already in use: stop whatever holds it before running `dev.py`. The launcher fails rather than picking another port.
- UI shows an error box: start the API with `dev.py`, or run `python scripts/run_pipeline.py --stage build` to regenerate `frontend/public/data/`.

Other docs: `README.md` (scoring method, limitations), `MVP.md` (scope, architecture, progress), `DEMO.md` (3-minute demo script).
