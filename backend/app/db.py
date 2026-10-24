"""SQLite helpers and schema (section 5 of the spec)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  id INTEGER PRIMARY KEY, pmid TEXT UNIQUE, doi TEXT, title TEXT NOT NULL, title_key TEXT,
  year INTEGER, source_url TEXT, fetched_at TEXT, fulltext_available INTEGER DEFAULT 0, text_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title_key);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE TABLE IF NOT EXISTS paper_drugs (paper_id INTEGER, drug TEXT, PRIMARY KEY (paper_id, drug));
CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY, paper_id INTEGER, drug TEXT, process TEXT, stage TEXT, direction TEXT,
  species TEXT, model_system TEXT, brain_region TEXT, markers TEXT, dose TEXT, duration TEXT, n TEXT,
  study_design TEXT, evidence_quote TEXT, quote_verified INTEGER, extractor_model TEXT,
  confidence_raw REAL, pathways TEXT
);
CREATE TABLE IF NOT EXISTS trials (
  id INTEGER PRIMARY KEY, drug TEXT, nct_id TEXT, phase TEXT, status TEXT, condition TEXT, source_url TEXT
);
CREATE TABLE IF NOT EXISTS drug_notes (drug TEXT PRIMARY KEY, bbb_note TEXT, safety_note TEXT, source_url TEXT);
CREATE TABLE IF NOT EXISTS checkpoints (stage TEXT, key TEXT, done_at TEXT, PRIMARY KEY (stage, key));
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or config.DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def is_done(con: sqlite3.Connection, stage: str, key: str) -> bool:
    return con.execute("SELECT 1 FROM checkpoints WHERE stage=? AND key=?", (stage, key)).fetchone() is not None


def mark_done(con: sqlite3.Connection, stage: str, key: str) -> None:
    con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?, ?, datetime('now'))", (stage, key))
    con.commit()
