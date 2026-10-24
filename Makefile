PY ?= .venv/Scripts/python

.PHONY: setup dev api web pipeline export test lint screens

setup:
	python -m venv .venv
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

# one command (cross-platform): API on :8000 and Vite on :5173, UI wired to the API
dev:
	$(PY) scripts/dev.py

api:
	$(PY) -m uvicorn app.main:app --app-dir backend --port 8000 --reload

web:
	cd frontend && npm run dev

pipeline:
	$(PY) scripts/run_pipeline.py

export:
	$(PY) scripts/export_static.py

test:
	$(PY) -m pytest backend/tests -q

lint:
	$(PY) -m ruff check backend scripts

screens:
	$(PY) scripts/screenshots.py
