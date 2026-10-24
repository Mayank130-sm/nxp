"""Per-drug ranking with a transparent score and a plain-language "why" string.

score = 100*mean(top-3 pro confidences) - 80*mean(top-3 anti confidences) - conflict penalty + pathway bonus."""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from typing import Any

from . import config
from .grade import detect_conflicts

PATHWAYS = {
    "BDNF/TrkB": r"bdnf|trkb",
    "Wnt/beta-catenin": r"wnt|catenin",
    "Notch": r"notch",
    "mTOR": r"mtor",
    "CREB": r"creb",
    "Shh": r"\bshh\b|sonic hedgehog",
}
PATHWAY_BONUS, PATHWAY_BONUS_CAP = 5.0, 15.0
ANTI_WEIGHT = 0.8
CONFLICT_PENALTY = {"strong": 10.0, "weak": 5.0}
CONFLICT_CAP = 25.0


def noisy_or(confidences: list[float]) -> float:
    """Combine independent evidence: 1 - prod(1 - c). Diminishing returns, bounded at 1."""
    p = 1.0
    for c in confidences:
        p *= 1 - c / 100
    return 1 - p


def top_mean(confidences: list[float], k: int = 3) -> float:
    """Mean of the k strongest per-paper confidences, as 0-1. Replication is already inside each claim's
    confidence, so quality (not claim count) drives the aggregate and the score cannot saturate."""
    top = sorted(confidences, reverse=True)[:k]
    return sum(top) / len(top) / 100 if top else 0.0


def best_per_paper(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Claims from one paper are not independent: keep the strongest per paper."""
    best: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r["paper_id"] not in best or r["confidence"] > best[r["paper_id"]]["confidence"]:
            best[r["paper_id"]] = r
    return list(best.values())


def pathway_hits(rows: list[dict[str, Any]]) -> list[str]:
    text = " ".join(r.get("pathways") or "" for r in rows)
    return [name for name, pat in PATHWAYS.items() if re.search(pat, text, re.IGNORECASE)]


def confidence_label(score: float) -> str:
    return "high" if score >= 55 else "moderate" if score >= 30 else "low"


def explain(d: dict[str, Any]) -> str:
    """Plain-language reason for the rank, built only from counted evidence."""
    bits = []
    if d["n_pro"]:
        bits.append(f"{d['n_pro']} paper{'s report' if d['n_pro'] != 1 else ' reports'} increased neurogenesis"
                    f" (best evidence: {d['top_design'] or 'design unknown'}, species {d['top_species'] or 'unknown'})")
    else:
        bits.append("no verified pro-neurogenic claims found")
    if d["n_anti"]:
        bits.append(f"{d['n_anti']} paper{'s report' if d['n_anti'] != 1 else ' reports'} decreased neurogenesis")
    if d["n_conflicts"]:
        bits.append(f"{d['n_conflicts']} stage(s) have conflicting findings, so the score is reduced")
    if d["pathways"]:
        bits.append(f"pathway evidence: {', '.join(d['pathways'])}")
    if d["safety_flag"]:
        bits.append("SAFETY FLAG: evidence suggests this drug may suppress neurogenesis")
    text = "; ".join(bits)
    return text[0].upper() + text[1:] + ". Hypothesis for lab testing, not a treatment claim."


def load_graded(con: sqlite3.Connection) -> list[dict[str, Any]]:
    q = ("SELECT c.*, s.confidence, s.replication, s.design AS g_design, s.markers AS g_markers, "
         "s.species AS g_species, s.dose AS g_dose, s.penalties FROM claims c "
         "JOIN claim_scores s ON s.claim_id=c.id WHERE c.quote_verified=1")
    return [dict(r) for r in con.execute(q)]


def rank_drugs(claims: list[dict[str, Any]], categories: dict[str, str], graded: bool = True,
               trials: dict[str, int] | None = None) -> list[dict[str, Any]]:
    by_drug: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in claims:
        by_drug[c["drug"]].append(c)
    conflicts = detect_conflicts(claims)
    out = []
    for drug in sorted(set(categories) | set(by_drug)):
        rows = by_drug.get(drug, [])
        pro = best_per_paper([r for r in rows if r["direction"] == "increase"])
        anti = best_per_paper([r for r in rows if r["direction"] == "decrease"])
        dconf = [c for c in conflicts if c["drug"] == drug]
        penalty = min(CONFLICT_CAP, sum(CONFLICT_PENALTY[c["severity"]] for c in dconf))
        paths = pathway_hits(pro)
        bonus = min(PATHWAY_BONUS_CAP, PATHWAY_BONUS * len(paths))
        pro_p, anti_p = top_mean([r["confidence"] for r in pro]), top_mean([r["confidence"] for r in anti])
        if graded:
            score = 100 * pro_p - 100 * ANTI_WEIGHT * anti_p - penalty + (bonus if pro else 0)
        else:  # ablation: raw vote counts, no grading
            n = len(pro) + len(anti)
            score = 100 * (len(pro) - len(anti)) / n * min(1.0, n / 5) if n else 0.0
        score = max(0.0, min(100.0, score))
        top = max(pro, key=lambda r: r["confidence"], default=None)
        parts = {k: round(sum(r[f"g_{k}" if k != "replication" else "replication"] for r in pro) / len(pro)
                          / config.WEIGHTS[k] * 100, 1) if pro else 0.0
                 for k in config.WEIGHTS}
        d = {
            "drug": drug, "category": categories.get(drug, "candidate"), "score": round(score, 1),
            "confidence_label": confidence_label(score), "n_pro": len(pro), "n_anti": len(anti),
            "n_claims": len(rows), "n_conflicts": len(dconf), "pathways": paths,
            "safety_flag": bool(anti) and anti_p >= pro_p, "breakdown": parts,
            "top_design": top["study_design"] if top else None, "top_species": top["species"] if top else None,
            "trials": (trials or {}).get(drug, 0),
        }
        d["why"] = explain(d)
        out.append(d)
    out.sort(key=lambda d: (-d["score"], d["safety_flag"], d["drug"]))
    for i, d in enumerate(out, 1):
        d["rank"] = i
    return out
