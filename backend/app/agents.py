"""TinyFish Agent jobs: (a) ClinicalTrials.gov trials, (b) drug label BBB/safety notes.

Total runs are capped by config.AGENT_RUN_CAP (default 30). Agent is used only where no API exists.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from . import db
from .models import Drug
from .tinyfish_client import AgentCapReached, TinyFishClient

TRIALS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"trials": {"type": "array", "items": {"type": "object", "properties": {
        "nct_id": {"type": "string"}, "phase": {"type": "string"}, "status": {"type": "string"},
        "condition": {"type": "string"}}}}},
}
NOTES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"bbb_note": {"type": "string"}, "safety_note": {"type": "string"},
                   "source_url": {"type": "string"}},
}
TRIALS_URL = "https://clinicaltrials.gov"
LABEL_URL = "https://dailymed.nlm.nih.gov"


def trials_goal(drug: str) -> str:
    return (f"On ClinicalTrials.gov search for the intervention '{drug}' with condition 'Alzheimer Disease'. "
            "Return JSON with up to 5 trials from the results table, each with nct_id, phase, status and "
            "condition, copied exactly as shown.")


def notes_goal(drug: str) -> str:
    return (f"Find the current drug label for '{drug}'. Return JSON with bbb_note (one sentence on whether the "
            "label says the drug crosses the blood-brain barrier or acts on the central nervous system; "
            "empty string if not stated), safety_note (one sentence on the main boxed or headline warning), "
            "and source_url of the label page. Do not guess.")


def save_trials(con: sqlite3.Connection, drug: str, result: dict[str, Any] | None, url: str) -> int:
    n = 0
    for t in (result or {}).get("trials") or []:
        if t.get("nct_id"):
            if con.execute("SELECT 1 FROM trials WHERE drug=? AND nct_id=?", (drug, t["nct_id"])).fetchone():
                continue
            con.execute("INSERT INTO trials(drug,nct_id,phase,status,condition,source_url) VALUES (?,?,?,?,?,?)",
                        (drug, t["nct_id"], t.get("phase"), t.get("status"), t.get("condition"),
                         f"https://clinicaltrials.gov/study/{t['nct_id']}"))
            n += 1
    return n


def save_notes(con: sqlite3.Connection, drug: str, result: dict[str, Any] | None) -> bool:
    r = result or {}
    if not (r.get("bbb_note") or r.get("safety_note")):
        return False
    con.execute("INSERT OR REPLACE INTO drug_notes VALUES (?,?,?,?)",
                (drug, r.get("bbb_note") or None, r.get("safety_note") or None, r.get("source_url") or None))
    return True


def run_agents(con: sqlite3.Connection, drugs: list[Drug], tf: TinyFishClient,
               n_trials: int = 20, n_notes: int = 10) -> dict[str, int]:
    """Fill gaps only: trials for drugs with none stored, label notes for drugs with none stored."""
    stats = {"runs": 0, "steps": 0, "trials": 0, "notes": 0, "failed": 0}
    have_trials = {r[0] for r in con.execute("SELECT DISTINCT drug FROM trials")}
    have_notes = {r[0] for r in con.execute("SELECT drug FROM drug_notes")}
    jobs = ([("trials", d) for d in drugs if d.name not in have_trials][:n_trials]
            + [("notes", d) for d in drugs if d.name not in have_notes][:n_notes])
    for kind, drug in jobs:
        if db.is_done(con, f"agent_{kind}_v3", drug.name):
            continue
        goal, url, schema = ((trials_goal(drug.name), TRIALS_URL, TRIALS_SCHEMA) if kind == "trials"
                             else (notes_goal(drug.name), LABEL_URL, NOTES_SCHEMA))
        try:
            run = tf.run_agent(url, goal, output_schema=schema)
        except AgentCapReached:
            print("[agents] run cap reached, stopping")
            break
        except RuntimeError as exc:
            print(f"[agents] {kind} {drug.name} failed: {exc}")
            stats["failed"] += 1
            continue
        stats["runs"] += 1
        stats["steps"] += run.get("num_of_steps") or 0
        if run.get("status") == "COMPLETED":
            if kind == "trials":
                stats["trials"] += save_trials(con, drug.name, run.get("result"), url)
            else:
                stats["notes"] += save_notes(con, drug.name, run.get("result"))
        else:
            stats["failed"] += 1
        con.commit()
        db.mark_done(con, f"agent_{kind}_v3", drug.name)
        print(f"[agents] {kind} {drug.name}: {run.get('status')} steps={run.get('num_of_steps')}")
    return stats
