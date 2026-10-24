"""Read-side logic shared by the FastAPI app and the static exporter."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from . import config
from .grade import detect_conflicts
from .graph import build_graph, to_json
from .ingest import load_drugs
from .rank import load_graded, rank_drugs
from .tinyfish_client import usage_summary

DISCLAIMER = "Hypothesis for lab testing, not a treatment claim."


def categories() -> dict[str, str]:
    return {d.name: d.category for d in load_drugs()}


def trial_counts(con: sqlite3.Connection) -> dict[str, int]:
    return {r["drug"]: r["n"] for r in con.execute("SELECT drug, COUNT(*) n FROM trials GROUP BY drug")}


def ranked_list(con: sqlite3.Connection, graded: bool = True) -> list[dict[str, Any]]:
    return rank_drugs(load_graded(con), categories(), graded=graded, trials=trial_counts(con))


def drug_detail(con: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    ranked = {d["drug"]: d for d in ranked_list(con)}
    if name not in ranked:
        return None
    claims = []
    q = ("SELECT c.*, s.confidence, s.penalties, p.pmid, p.doi, p.title, p.year, p.source_url "
         "FROM claims c JOIN claim_scores s ON s.claim_id=c.id JOIN papers p ON p.id=c.paper_id "
         "WHERE c.drug=? AND c.quote_verified=1 ORDER BY s.confidence DESC")
    for r in con.execute(q, (name,)):
        claims.append(dict(r))
    note = con.execute("SELECT * FROM drug_notes WHERE drug=?", (name,)).fetchone()
    return {
        **ranked[name],
        "claims": claims,
        "conflicts": detect_conflicts(claims),
        "trials": [dict(r) for r in con.execute("SELECT * FROM trials WHERE drug=?", (name,))],
        "notes": dict(note) if note else None,
        "disclaimer": DISCLAIMER,
    }


def graph_json(con: sqlite3.Connection) -> dict[str, Any]:
    return to_json(build_graph(load_graded(con), ranked_list(con)))


def _read_json(path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stats(con: sqlite3.Connection) -> dict[str, Any]:
    one = lambda sql: con.execute(sql).fetchone()[0]
    ranked = ranked_list(con)
    return {
        "papers": one("SELECT COUNT(*) FROM papers"),
        "papers_fulltext": one("SELECT COALESCE(SUM(fulltext_available),0) FROM papers"),
        "papers_with_claims": one("SELECT COUNT(DISTINCT paper_id) FROM claims"),
        "claims_verified": one("SELECT COUNT(*) FROM claims WHERE quote_verified=1"),
        "drugs_scored": sum(1 for d in ranked if d["n_claims"] > 0),
        "drugs_total": len(ranked),
        "conflicts": sum(d["n_conflicts"] for d in ranked),
        "tinyfish": usage_summary(),
        "weights": config.WEIGHTS,
        "penalties": config.PENALTIES,
        "validation": _read_json(config.RESULTS_DIR / "validation.json"),
        "extraction_eval": _read_json(config.RESULTS_DIR / "extraction_eval.json"),
        "extractor_model": config.OLLAMA_MODEL,
        "disclaimer": DISCLAIMER,
    }
