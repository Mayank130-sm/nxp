"""Claim extraction tuned for precision: keyword gate -> strict-schema LLM -> quote grounding."""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Any

import httpx

from . import config, db
from .llm import LLM
from .models import Drug

NEURO_VOCAB = re.compile(
    r"neurogenesis|neurogenic|BrdU|EdU|Ki-?67|DCX|doublecortin|NeuN|neural (stem|progenitor)|"
    r"neural precursor|neuroblast|dentate gyrus|subventricular|subgranular|\bSVZ\b|\bSGZ\b|"
    r"proliferation|NSCs?\b|NPCs?\b|adult-born|newborn (neurons|cells)",
    re.IGNORECASE,
)
PATHWAYS = ("BDNF", "TrkB", "Wnt", "beta-catenin", "Notch", "mTOR", "CREB", "Shh", "Sonic hedgehog")

CLAIM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "has_claim": {"type": "boolean"},
        "drug": {"type": ["string", "null"]},
        "stage": {"enum": ["proliferation", "survival", "differentiation", "general", None]},
        "direction": {"enum": ["increase", "decrease", "no_effect", "mixed", None]},
        "species": {"type": ["string", "null"]},
        "model_system": {"type": ["string", "null"]},
        "brain_region": {"type": ["string", "null"]},
        "markers": {"type": "array", "items": {"type": "string"}},
        "pathways": {"type": "array", "items": {"type": "string"}},
        "dose": {"type": ["string", "null"]},
        "duration": {"type": ["string", "null"]},
        "n": {"type": ["string", "null"]},
        "study_design": {"enum": ["in_vitro", "rodent", "nonhuman_primate", "human_cells_organoid",
                                  "human_clinical", "review_or_meta", None]},
        "evidence_quote": {"type": ["string", "null"]},
        "confidence_raw": {"type": ["number", "null"]},
    },
    "required": ["has_claim", "drug", "stage", "direction", "evidence_quote"],
}

GATE_SCHEMA: dict[str, Any] = {
    "type": "object", "properties": {"reports_effect": {"type": "boolean"}}, "required": ["reports_effect"],
}
GATE_SYSTEM = (
    "Answer with JSON only. reports_effect is true only if the text explicitly states a result of the "
    "named DRUG on neurogenesis or on neural stem/progenitor cell proliferation, survival or differentiation "
    "(an increase, a decrease or no change). Background statements, methods, other drugs, and "
    "speculation are false."
)

SYSTEM = (
    "You extract claims about whether a DRUG changes adult neurogenesis from scientific text. "
    "Return a single JSON object. Set has_claim=false unless the text explicitly reports an effect of the "
    "named drug on neurogenesis, neural stem/progenitor proliferation, survival or differentiation. "
    "If the text does not state a field, return null (or [] for lists). Do not infer. "
    "evidence_quote must be copied VERBATIM from the text, one or two sentences, no edits. "
    "direction: increase, decrease, no_effect or mixed, as stated for the drug. It is the change in the "
    "neurogenesis measure itself (not behaviour or symptoms) and a drug that reverses a reduction is an increase. "
    "stage: proliferation, survival, differentiation, or general. "
    "markers: only markers named in the text (e.g. BrdU, Ki67, DCX, NeuN). "
    "pathways: only pathways named in the text. "
    "confidence_raw: 0-1 how explicit the statement is."
)


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def verify_quote(quote: str | None, source: str) -> bool:
    """Quote must be a substring of the source after whitespace normalisation."""
    if not quote or len(norm_ws(quote)) < 15:
        return False
    return norm_ws(quote) in norm_ws(source)


def drug_pattern(drug: Drug) -> re.Pattern[str]:
    names = [drug.name, *drug.synonyms]
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names if len(n) > 1) + r")\b", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"[#*_>`]+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])", norm_ws(text))
    return [p for p in parts if 25 <= len(p) <= 800]


def build_windows(text: str, drug: Drug, max_windows: int = 12) -> list[str]:
    """Sentence windows (sentence plus preceding one) that pass the drug AND neurogenesis keyword gate."""
    pat = drug_pattern(drug)
    sents = split_sentences(text)
    scored: list[tuple[int, str]] = []
    for i, s in enumerate(sents):
        window = f"{sents[i - 1]} {s}" if i else s
        if pat.search(window) and NEURO_VOCAB.search(s):
            scored.append((len(NEURO_VOCAB.findall(s)) + (2 if pat.search(s) else 0), window))
    scored.sort(key=lambda t: -t[0])
    seen, out = set(), []
    for _, w in scored:
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= max_windows:
            break
    return out


SPECIES_PATTERNS = {
    "mouse": r"\b(mice|mouse|murine)\b",
    "rat": r"\b(rats?|sprague|wistar)\b",
    "human": r"\b(humans?|patients?|participants|volunteers|iPSC|hiPSC)\b",
    "monkey": r"\b(monkeys?|macaques?|marmosets?|primates?)\b",
    "zebrafish": r"\bzebrafish\b",
}


def paper_context(text: str, title: str = "") -> dict[str, str | None]:
    """Deterministic paper-level species / study design from word counts (fallback when a claim sentence
    does not state them). Only counts words present in the text; never guesses beyond that."""
    counts = {k: len(re.findall(p, text, re.IGNORECASE)) for k, p in SPECIES_PATTERNS.items()}
    species = max(counts, key=lambda k: counts[k]) if any(counts.values()) else None
    if species and counts[species] < 2:
        species = None
    head = f"{title} {text[:600]}".lower()
    in_vitro = len(re.findall(r"in vitro|cultured|culture|cell line|neurospheres?", text, re.IGNORECASE))
    if re.search(r"meta-analysis|systematic review|\breview\b", head):
        design = "review_or_meta"
    elif species in ("mouse", "rat", "zebrafish"):
        design = "rodent" if species != "zebrafish" else "in_vitro"
    elif species == "monkey":
        design = "nonhuman_primate"
    elif species == "human":
        design = ("human_clinical" if re.search(r"randomi[sz]ed|clinical trial|cohort|patients", text, re.IGNORECASE)
                  else "human_cells_organoid")
    else:
        design = "in_vitro" if in_vitro >= 3 else None
    return {"species": species, "study_design": design}


def validate_claim(raw: dict[str, Any], window: str, drug: Drug) -> dict[str, Any] | None:
    """Return a clean claim dict, or None if it fails any precision check."""
    if not raw.get("has_claim") or raw.get("direction") is None:
        return None
    quote = raw.get("evidence_quote")
    if not verify_quote(quote, window):
        return None
    if not drug_pattern(drug).search(window):
        return None
    return {
        "drug": drug.name,
        "stage": raw.get("stage") or "general",
        "direction": raw["direction"],
        "species": raw.get("species"),
        "model_system": raw.get("model_system"),
        "brain_region": raw.get("brain_region"),
        "markers": ", ".join(raw.get("markers") or []) or None,
        "pathways": ", ".join(p for p in (raw.get("pathways") or []) if p) or None,
        "dose": raw.get("dose"),
        "duration": raw.get("duration"),
        "n": raw.get("n"),
        "study_design": raw.get("study_design"),
        "evidence_quote": norm_ws(quote),
        "quote_verified": 1,
        "confidence_raw": raw.get("confidence_raw"),
    }


def extract_window(llm: LLM, drug: Drug, window: str, counts: dict[str, int] | None = None
                   ) -> dict[str, Any] | None:
    """Two passes: cheap yes/no gate, then full extraction. `counts` tallies the funnel for validation."""
    counts = counts if counts is not None else {}
    bump = lambda k: counts.__setitem__(k, counts.get(k, 0) + 1)
    prompt = f"DRUG: {drug.name}\n\nTEXT:\n{window}"
    bump("windows")
    try:
        # pass 1: cheap yes/no (about 5 output tokens) so most windows never pay for the full JSON
        if not llm.complete_json(GATE_SYSTEM, prompt, GATE_SCHEMA).get("reports_effect"):
            return None
        bump("gate_pass")
        raw = llm.complete_json(SYSTEM, prompt, CLAIM_SCHEMA)
    except (ValueError, KeyError, httpx.HTTPError) as exc:  # malformed JSON or Ollama error: skip window
        print(f"  [extract] LLM error, skipping window: {exc.__class__.__name__}")
        bump("errors")
        return None
    if raw.get("has_claim") and raw.get("direction") is not None:
        bump("proposed")
        if not verify_quote(raw.get("evidence_quote"), window):
            bump("quote_failed")
    claim = validate_claim(raw, window, drug)
    if claim:
        bump("verified")
    return claim


def is_duplicate(quote: str, seen: list[str]) -> bool:
    """Overlapping windows repeat sentences; treat identical or containing quotes as the same claim."""
    q = quote.lower()
    return any(q in s or s in q for s in seen)


def run_extract(con: sqlite3.Connection, drugs: list[Drug], llm: LLM, max_windows: int = 12) -> None:
    by_name = {d.name: d for d in drugs}
    rows = con.execute(
        "SELECT p.id, p.text_path, pd.drug FROM papers p JOIN paper_drugs pd ON pd.paper_id=p.id "
        "WHERE p.text_path IS NOT NULL ORDER BY pd.drug, p.id").fetchall()
    for row in rows:
        drug = by_name.get(row["drug"])
        key = f"{row['id']}:{row['drug']}"
        if drug is None or db.is_done(con, "extract", key):
            continue
        text = (config.ROOT / row["text_path"]).read_text(encoding="utf-8")
        ctx = paper_context(text, text.split(chr(10), 1)[0])
        kept, counts, seen = 0, {}, []
        for window in build_windows(text, drug, max_windows):
            claim = extract_window(llm, drug, window, counts)
            if claim is None or is_duplicate(claim["evidence_quote"], seen):
                continue
            seen.append(claim["evidence_quote"].lower())
            for field, value in ctx.items():
                claim[field] = claim.get(field) or value
            claim.update(paper_id=row["id"], extractor_model=llm.model, process="neurogenesis")
            cols = ", ".join(claim)
            con.execute(f"INSERT INTO claims({cols}) VALUES ({', '.join('?' * len(claim))})",
                        list(claim.values()))
            kept += 1
        con.execute("INSERT OR REPLACE INTO extract_stats VALUES (?,?,?,?,?,?,?)",
                    (row["id"], row["drug"], counts.get("windows", 0), counts.get("gate_pass", 0),
                     counts.get("proposed", 0), counts.get("quote_failed", 0), kept))
        con.commit()
        db.mark_done(con, "extract", key)
        print(f"[extract] paper {row['id']} / {row['drug']}: {kept} claims")
