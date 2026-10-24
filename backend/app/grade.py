"""Evidence grading (0-100 per claim) and contradiction detection. Weights live in config.py."""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from typing import Any

from . import config

DESIGN_SCORE = {
    "human_clinical": 1.0, "nonhuman_primate": 0.8, "human_cells_organoid": 0.7,
    "rodent": 0.6, "in_vitro": 0.4, "review_or_meta": 0.3,
}
SPECIES_SCORE = {"human": 1.0, "monkey": 0.8, "mouse": 0.6, "rat": 0.6, "zebrafish": 0.3}
MARKER_GROUPS = {
    "proliferation": r"brdu|edu|ki-?67|pcna|ph3",
    "immature": r"dcx|doublecortin|psa-?ncam|tuj1|tbr2",
    "mature": r"neun|calbindin|calretinin|map2",
    "stem": r"sox2|nestin|gfap|musashi",
}
# Drugs with documented central-nervous-system penetration are scored from drug_notes.bbb_note text.
BBB_POSITIVE = re.compile(r"cross(es)?|penetrat|brain|cns|central nervous", re.IGNORECASE)
BBB_NEGATIVE = re.compile(r"poor(ly)? (penetrat|cross)|does not cross|limited (brain|cns)|not cross", re.IGNORECASE)


BBB_UNSTATED = re.compile(r"(does|do) not (explicitly )?(state|mention|say)|not (explicitly )?stated|no mention", re.IGNORECASE)


def marker_score(markers: str | None) -> float:
    """Distinct marker classes (proliferation / immature / mature / stem), 3 classes = full marks."""
    if not markers:
        return 0.0
    hit = sum(1 for pat in MARKER_GROUPS.values() if re.search(pat, markers, re.IGNORECASE))
    return min(hit / 3, 1.0)


def replication_score(n_papers: int) -> float:
    return {0: 0.0, 1: 0.2, 2: 0.6}.get(n_papers, 1.0)


def dose_bbb_score(dose: str | None, bbb_note: str | None) -> float:
    score = 0.5 if dose else 0.0
    if bbb_note:
        if BBB_UNSTATED.search(bbb_note):
            score += 0.15  # label is silent: same as unknown
        elif BBB_NEGATIVE.search(bbb_note):
            score += 0.0
        elif BBB_POSITIVE.search(bbb_note):
            score += 0.5
        else:
            score += 0.15
    else:
        score += 0.15  # BBB unknown: small neutral credit, never full marks
    return score


def grade_claim(claim: dict[str, Any], n_papers: int, in_conflict: bool, bbb_note: str | None = None
                ) -> dict[str, Any]:
    """Return the component breakdown and final 0-100 confidence for one claim."""
    w = config.WEIGHTS
    parts = {
        "replication": w["replication"] * replication_score(n_papers),
        "design": w["design"] * DESIGN_SCORE.get(claim.get("study_design") or "", 0.2),
        "markers": w["markers"] * marker_score(claim.get("markers")),
        "species": w["species"] * SPECIES_SCORE.get(claim.get("species") or "", 0.2),
        "dose": w["dose"] * dose_bbb_score(claim.get("dose"), bbb_note),
    }
    penalties = {}
    if n_papers <= 1:
        penalties["single_lab"] = config.PENALTIES["single_lab"]
    if in_conflict:
        penalties["contradiction"] = config.PENALTIES["contradiction"]
    if not claim.get("quote_verified"):
        penalties["unverified_quote"] = config.PENALTIES["unverified_quote"]
    total = max(0.0, min(100.0, sum(parts.values()) - sum(penalties.values())))
    return {"confidence": round(total, 1), "parts": {k: round(v, 1) for k, v in parts.items()},
            "penalties": penalties}


def detect_conflicts(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag (drug, stage) groups whose verified claims disagree in direction.

    severity = "strong" when both increase and decrease are reported, "weak" when one side is
    no_effect. Conflicting claims are returned side by side, never hidden.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in claims:
        if c.get("quote_verified"):
            groups[(c["drug"], c["stage"] or "general")].append(c)
    out = []
    for (drug, stage), rows in groups.items():
        dirs = {r["direction"] for r in rows} & {"increase", "decrease", "no_effect"}
        if len(dirs) < 2:
            continue
        strong = {"increase", "decrease"} <= dirs
        out.append({
            "drug": drug, "stage": stage, "severity": "strong" if strong else "weak",
            "sides": {d: [r for r in rows if r["direction"] == d] for d in sorted(dirs)},
        })
    return out


def grade_all(con: sqlite3.Connection) -> int:
    """Grade every verified claim and (re)write claim_scores. Returns number of claims graded."""
    claims = [dict(r) for r in con.execute("SELECT * FROM claims WHERE quote_verified=1")]
    notes = {r["drug"]: r["bbb_note"] for r in con.execute("SELECT drug, bbb_note FROM drug_notes")}
    conflicts = detect_conflicts(claims)
    conflicted = {(c["drug"], c["stage"]) for c in conflicts}
    support: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    for c in claims:
        support[(c["drug"], c["stage"] or "general", c["direction"])].add(c["paper_id"])
    con.execute("DELETE FROM claim_scores")
    for c in claims:
        key = (c["drug"], c["stage"] or "general", c["direction"])
        g = grade_claim(c, len(support[key]), (c["drug"], c["stage"] or "general") in conflicted,
                        notes.get(c["drug"]))
        p = g["parts"]
        con.execute("INSERT INTO claim_scores VALUES (?,?,?,?,?,?,?,?)",
                    (c["id"], g["confidence"], p["replication"], p["design"], p["markers"], p["species"],
                     p["dose"], ",".join(g["penalties"])))
    con.commit()
    return len(claims)
