# MASTER PROMPT: Build NeuroRx end to end (24-hour hackathon build)
do commits regularly in github associated in this folder.
---

## 0. Role and mission

You are my senior engineer and pair-programmer. In **under 24 hours of wall-clock time** we will build **NeuroRx**: an evidence-graded drug-repurposing knowledge graph for **neurogenesis in Alzheimer's disease**, with a React + FastAPI demo and a **real TinyFish API integration**. I am a second-year CS undergraduate, so explain non-obvious decisions in one or two lines and keep the code readable.

**One-line pitch:** NeuroRx turns scattered, contradictory neurogenesis literature into a searchable graph where every drug-to-neurogenesis claim is linked to a paper, given a confidence grade, and flagged when contradicted, so labs can decide which approved drugs deserve testing.

**Honesty rule (non-negotiable):** every output is a *hypothesis for lab testing*, never a treatment claim. Never invent papers, PMIDs, doses, quotes or numbers. If data is missing, show "unknown".

## 1. Fixed decisions (do not re-ask)

- Disease focus: **Alzheimer's disease**. Process focus: **adult neurogenesis** (proliferation, survival, differentiation).
- Extraction LLM: **local Ollama**, model set by env var `OLLAMA_MODEL` (default `qwen2.5:7b-instruct`; allow bigger models). Put the LLM behind a small interface so a hosted model could be swapped in later.
- Backend: **FastAPI (Python 3.11)**. Frontend: **React + Vite + TypeScript**.
- Storage: **SQLite** for papers and claims, **NetworkX** for the graph (export to `data/graph.json`). No Neo4j, no Postgres, no Docker required.
- Web access layer: **TinyFish** (section 4). PubMed E-utilities stays as the abstract backbone.
- Budget: assume free tiers only.

## 2. Time-boxed plan

Work phase by phase. Finish each phase's acceptance check before moving on. If a phase overruns by 30 percent, **cut scope using section 9, don't extend the schedule**. Commit after every phase.

| Phase | Hours | Goal |
|---|---|---|
| P0 | 0-1.5 | Repo scaffold, env, TinyFish smoke test, Ollama smoke test |
| P1 | 1.5-5 | Ingestion: seed drug list to Search to Fetch to cached papers |
| P2 | 5-10 | Extraction: sentence-level LLM claims, grounded and validated |
| P3 | 10-13 | Evidence grading, contradiction flags, ranking |
| P4 | 13-19 | FastAPI + React UI (hero + ranking, drug detail, graph, methods), design polish, screenshots |
| P5 | 19-21.5 | Validation against controls, metrics, `results/` report |
| P6 | 21.5-24 | README, demo script, static fallback build, final polish |

Before writing code, **print the plan back to me and list any assumption you are making**. Then start P0 without waiting unless something blocks you.

## 3. Repo layout

```
neurorx/
  README.md
  .env.example            # TINYFISH_API_KEY, OLLAMA_MODEL, OLLAMA_HOST, NCBI_EMAIL, NCBI_API_KEY (optional)
  backend/
    app/main.py           # FastAPI
    app/config.py
    app/db.py             # SQLite helpers
    app/models.py         # pydantic schemas
    app/tinyfish_client.py
    app/pubmed.py
    app/ingest.py
    app/extract.py
    app/grade.py
    app/graph.py
    app/rank.py
    app/llm.py            # Ollama interface
    tests/
  scripts/
    smoke_tinyfish.py
    smoke_ollama.py
    run_pipeline.py       # ingest -> extract -> grade -> graph -> rank, resumable
    export_static.py      # writes frontend/public/data/*.json
  data/
    seed_drugs.csv
    labels/gold_sentences.csv   # ~100 hand-labelled sentences (I will fill in; you generate the template)
    cache/                # raw fetched pages (gitignored)
  frontend/               # Vite React TS
  results/                # validation report, metrics, figures
```

## 4. TinyFish integration (the core requirement; do this properly)

**Step 1: read the docs first.** Before writing the client, read `https://docs.tinyfish.ai/llms.txt` and the Search, Fetch and Agent API pages it links to. Treat the live docs as the source of truth. Use only request and response fields you have verified there, and tell me where the docs differ from what is below.

What I know so far (verify it):
- One API key (`X-API-Key` header) covers four products: **Search** (`GET https://api.search.tinyfish.ai?query=...&location=US&language=en`), **Fetch** (`POST https://api.fetch.tinyfish.ai` with `{"urls": [...]}`, output as markdown/html/json), **Agent** (`POST https://agent.tinyfish.ai/v1/automation/run-sse`, also `/run` and `/run-async`; takes a URL and a natural-language goal and returns structured JSON), **Browser** (`POST https://api.browser.tinyfish.ai`, remote Playwright/CDP session).
- Python SDK: `from tinyfish import TinyFish`; `client = TinyFish()`; `client.search.query(query=...)`.
- Search and Fetch are reported as free with rate limits (reportedly about 30 search/min and 150 fetch/min); Agent and Browser use credits. Respect rate limits with a token-bucket limiter and exponential backoff on 429/5xx.

**Build `tinyfish_client.py`** as a thin, typed wrapper with: `search(query)`, `fetch(urls, fmt="markdown")`, `run_agent(url, goal, stream=False)`. Requirements:
- API key only from env; never log it; fail with a clear message if missing.
- On-disk cache keyed by hash of (endpoint, params) in `data/cache/` so we never pay or wait twice.
- Retries, timeouts, and a `--dry-run` mode that returns cached data only.
- Log every call (endpoint, latency, cache hit, status) to `data/tinyfish_calls.jsonl` so I can quote real usage numbers in the pitch.

**Where each product is used in the pipeline:**
1. **Search**: for each drug x stage, run queries like `"<drug> adult hippocampal neurogenesis DCX BrdU"`, `"<drug> neural stem cell proliferation Alzheimer"`, `"<drug> neurogenesis impairment"`. Collect ranked URLs and snippets; prefer open-access hosts (PMC, Europe PMC, bioRxiv, journal OA pages).
2. **Fetch**: convert the top URLs to clean Markdown, keep the **Abstract, Methods and Results** sections (Methods holds species, dose, markers). Store raw text plus the source URL and fetch timestamp.
3. **Agent**: use it only where no API exists, with exactly two jobs: (a) ClinicalTrials.gov: goal "list trials for `<drug>` in Alzheimer's or cognitive impairment with status and phase, return JSON", (b) drug label or DrugBank-style pages for blood-brain-barrier and safety notes. Cap total agent runs (default 30) via config and report credits used.
4. **Browser**: **optional stretch only**. Skip unless everything else is done.

Add `scripts/smoke_tinyfish.py` that runs one real search, one real fetch and one real agent goal, and prints the results. **Run it in P0 and show me the output.** If it fails, stop and tell me what you need (usually a key at agent.tinyfish.ai/api-keys).

Also pull abstracts from **PubMed E-utilities** (`esearch` + `efetch`, polite rate limit, `NCBI_EMAIL`). Merge records by PMID or DOI; dedupe by URL.

## 5. Data model (SQLite)

- `papers(id, pmid, doi, title, year, source_url, fetched_at, fulltext_available, text_path)`
- `claims(id, paper_id, drug, process, stage, direction, species, model_system, brain_region, markers, dose, duration, n, study_design, evidence_quote, quote_verified, extractor_model, confidence_raw)`
  - `stage` in {proliferation, survival, differentiation, general}
  - `direction` in {increase, decrease, no_effect, mixed}
  - `study_design` in {in_vitro, rodent, nonhuman_primate, human_cells_organoid, human_clinical, review_or_meta}
- `trials(id, drug, nct_id, phase, status, condition, source_url)`
- `drug_notes(drug, bbb_note, safety_note, source_url)`

## 6. Extraction (the part that decides quality)

My earlier local-LLM extractor on a 3B model hit only about 33-38% accuracy, so **design for precision, not recall**:
- Split text into **sentences/short windows**; pre-filter with a keyword gate (drug name or synonym + neurogenesis vocabulary: neurogenesis, BrdU, Ki67, DCX, NeuN, neural stem/progenitor, dentate gyrus, SVZ, proliferation).
- Prompt the LLM with a **strict JSON schema** (use Ollama structured output / `format` if available), temperature 0, one claim per sentence window, `null` for unknown fields, and an explicit instruction: *"If the text does not state it, return null. Do not infer."*
- **Quote grounding:** the model must return the exact `evidence_quote`. Programmatically check the quote is a substring of the source (after whitespace normalisation). Set `quote_verified`; **discard claims whose quote does not verify.**
- Normalise drug names with a synonym table in `seed_drugs.csv` (brand/generic names).
- Write checkpoints so the run is **resumable** and safe to Ctrl-C.
- Create `data/labels/gold_sentences.csv` (a template, about 100 rows to be filled by me) and `scripts/eval_extraction.py` that computes precision/recall/F1 per field against it.

## 7. Evidence grading, contradictions, ranking

**Per-claim confidence (0-100)**, computed in `grade.py`, with weights in `config.py` and **documented in the README**:
- Replication across independent papers: 25
- Study design (human-relevant above rodent above in vitro): 25
- Marker validity (multiple markers, e.g. BrdU/Ki67 plus DCX plus NeuN, beats a single marker): 20
- Species relevance: 20
- Dose/BBB plausibility: 10
- Penalties: single-lab result, contradiction present, quote unverified.

**Contradiction detector:** for each (drug, stage), flag a conflict when verified claims disagree in direction. Output the conflicting claims side by side with their species/markers. Do not hide them.

**Ranking (`rank.py`):** per drug, aggregate confidence for pro-neurogenic claims, subtract anti-neurogenic and contradiction penalties, add a pathway-hit bonus (BDNF/TrkB, Wnt/beta-catenin, Notch, mTOR, CREB, Shh) when pathway claims were extracted. Output a score **and a plain-language "why"** string. Mark drugs known to *suppress* neurogenesis as **safety flags**, not opportunities.

**Graph (`graph.py`):** nodes = Drug, Pathway, Stage, Disease; edges carry aggregated evidence and claim ids. Skip PyKEEN unless there is time left (section 9); a transparent score beats an unexplained embedding for judges.

## 8. API and UI

**FastAPI endpoints:** `GET /drugs` (ranked list), `GET /drugs/{name}` (claims, conflicts, trials, notes, score breakdown), `GET /graph`, `GET /stats` (counts, TinyFish usage, validation metrics), `GET /health`. CORS enabled for the dev server.

**React UI: few screens, but each one must look premium. The UI is half of how judges will score this, so spend real effort on it.**

*Design direction: dark, luxury, scientific.* Think a refined research instrument, not a generic dashboard template.
- **Stack:** Vite + React + TypeScript + Tailwind CSS + shadcn/ui primitives, `framer-motion` for motion, `lucide-react` icons, `react-force-graph-2d` for the graph, a small chart lib (Recharts or visx) for score bars. If a `frontend-design` skill is available, use it before writing UI code.
- **Palette (CSS variables, define once):** background near-black navy `#0B0A1F` to `#15112E`; surface cards `#1B1740` with 1px borders at low-opacity white; text off-white `#F1F0FA`, muted `#9A97C4`; accents teal `#14A596` (positive / pro-neurogenic), violet `#6B5BD2` (pathways, primary actions), amber `#F2B84B` (moderate / highlights), coral `#F0645F` (conflicts / safety flags). Use accents sparingly so the page feels calm and expensive.
- **Type:** a refined serif for headings (e.g. Fraunces or Cormorant Garamond) with Inter for UI text; tabular numerals for scores; generous letter-spacing on small caps labels. Load via Google Fonts with a system fallback.
- **Surface details:** soft inner glow and subtle gradient on the hero and top cards, fine 1px borders, large radii (16-20px), layered shadows, a faint noise or grid texture behind the hero. No default-looking tables or browser-blue links.
- **Motion:** staggered fade-up on page load, animated count-up for scores, score rings and bars that fill on mount, smooth hover lift on cards, graph nodes that ease into place. Respect `prefers-reduced-motion`. Keep every animation under about 600 ms.
- **Responsive and accessible:** works at laptop and phone width, keyboard navigable, contrast at least AA, visible focus states, meaningful `alt`/`aria` labels.

*Screens:*
1. **Landing/Hero + Ranking:** a hero with the one-line pitch, three live stat tiles from `/stats` (papers processed, verified claims, drugs scored), and a prominent search box. Below it, the ranked drug list as **cards or a refined table**: drug name, animated score ring, confidence badge, evidence-count chip, conflict badge (coral) and safety badge. Filters by direction, study design and species; sort by score. Skeleton loaders, never a blank flash.
2. **Drug detail:** a header with the score ring and a plain-language "why this ranks here" sentence; a **score breakdown** (replication, design, markers, species, dose) as animated bars; an **evidence timeline/list** where each item shows species, markers, dose, region, a highlighted verbatim quote, a verified-quote tick, and a PMID/DOI link; a **side-by-side conflict panel** when studies disagree; trials and BBB/safety notes; and a clear disclaimer strip: "Hypothesis for lab testing, not a treatment claim".
3. **Graph explorer:** full-bleed dark canvas, nodes coloured by type (drug teal, pathway violet, stage amber, disease coral), edge thickness = confidence, hover tooltips, click opens a slide-over evidence drawer. Add a legend, zoom/reset controls and a "focus on this drug" mode.
4. **Methods and Validation:** the scoring weights shown visually, validation results (control recovery table, extraction precision/recall) as clean charts, the honesty statement, and a "Powered by TinyFish" panel that shows **real** Search / Fetch / Agent call counts from `/stats` with a tiny pipeline diagram.
- **UI quality gate (P4 acceptance):** take screenshots of every screen at desktop and mobile widths with Playwright, review them yourself, fix any overflow, low contrast, misalignment or empty-state ugliness, and save the final screenshots to `results/screens/` (I will use them in the slides). Provide good empty, loading and error states.
- **Must work without the backend:** `scripts/export_static.py` writes JSON to `frontend/public/data/` and the app falls back to it when `VITE_API_URL` is unset. This lets us deploy the frontend alone on Vercel, so judges can open a link even though Ollama can't run there.

## 9. Scope cuts, in this order, if we fall behind

1. Drop the Browser product and PyKEEN.
2. Shrink the corpus (target **about 300 papers and about 25 drugs**; fall back to about 150 and 12).
3. Drop the trials/Agent branch except one working demo drug.
4. Simplify the Graph page to a static, non-interactive view; keep ranking and detail. **Never cut UI polish on the ranking and detail pages.**
Never cut: TinyFish Search+Fetch in the live pipeline, quote grounding, contradiction flags, validation against controls, the honesty statement.

## 10. Validation (what makes the submission credible)

- **Positive controls** (the pipeline should surface pro-neurogenic evidence): fluoxetine, lithium, metformin, memantine. **Negative controls** (should surface suppression or safety flags): dexamethasone, morphine, ethanol. These come from general literature knowledge, so let the data confirm or refute them. If the pipeline disagrees, report that honestly and investigate rather than tuning until it agrees.
- Report: extraction precision/recall on the gold set; fraction of claims with verified quotes; control recovery table; ablation of ranking **with vs. without evidence grading**.
- Write all of it to `results/validation.md` with real numbers, and expose a summary through `/stats`.

## 11. Engineering rules

- Python: type hints, `ruff`-clean, small functions. Tests (`pytest`) for: quote verification, grading math, contradiction detection, TinyFish client caching and retry (mock HTTP), and one end-to-end test on a 5-paper fixture.
- Secrets only via `.env`; `.env`, `data/cache/` and the DB are gitignored; ship `.env.example`.
- Don't scrape anything outside the TinyFish APIs and PubMed E-utilities; respect site terms; store full text only for open-access papers and otherwise keep just the abstract and the URL.
- After each phase: run the tests, show me the acceptance result, make a git commit with a clear message. If you change the plan, say why in one line.
- When blocked on something only I can provide (API key, labelled data, a decision), stop and ask one specific question, then continue with a stub where possible.

## 12. Final deliverables checklist

- [ ] Running backend + frontend with a one-command start (`make dev` or documented steps)
- [ ] `scripts/run_pipeline.py` reproduces the graph from scratch
- [ ] Static export deployable to Vercel
- [ ] UI screenshots (desktop + mobile) in `results/screens/` for the slides
- [ ] `README.md`: problem, architecture diagram (Mermaid), TinyFish usage, setup, scoring method, limitations, honesty statement
- [ ] `results/validation.md` with real metrics
- [ ] `data/tinyfish_calls.jsonl` summarised into the real numbers for the pitch
- [ ] `DEMO.md`: a 3-minute demo script that follows the slide order (problem, solution, users, architecture, TinyFish, scalability and use case)
- [ ] A short list of the top 5 numbers I should update in my slides (papers processed, claims verified, controls recovered, TinyFish calls, extraction precision)

**Start now:** print your plan and assumptions (max 20 lines), then begin P0.
