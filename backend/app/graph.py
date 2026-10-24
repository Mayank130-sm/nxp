"""Knowledge graph (NetworkX): Drug, Pathway, Stage, Disease nodes; edges carry aggregated evidence."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import networkx as nx

from . import config
from .rank import PATHWAYS, best_per_paper, noisy_or

DISEASE = "Alzheimer's disease"
STAGES = ("proliferation", "survival", "differentiation", "general")


def _edge_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    inc = best_per_paper([r for r in rows if r["direction"] == "increase"])
    dec = best_per_paper([r for r in rows if r["direction"] == "decrease"])
    pro, anti = noisy_or([r["confidence"] for r in inc]), noisy_or([r["confidence"] for r in dec])
    return {
        "direction": "increase" if pro >= anti else "decrease",
        "confidence": round(100 * max(pro, anti), 1),
        "n_claims": len(rows), "n_increase": len(inc), "n_decrease": len(dec),
        "claim_ids": [r["id"] for r in rows],
    }


def build_graph(claims: list[dict[str, Any]], ranked: list[dict[str, Any]]) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node(f"disease:{DISEASE}", type="disease", label=DISEASE)
    for s in STAGES:
        g.add_node(f"stage:{s}", type="stage", label=s)
    for p in PATHWAYS:
        g.add_node(f"pathway:{p}", type="pathway", label=p)
    for d in ranked:
        if d["n_claims"] == 0:
            continue
        g.add_node(f"drug:{d['drug']}", type="drug", label=d["drug"], score=d["score"],
                   safety_flag=d["safety_flag"], category=d["category"])
        g.add_edge(f"drug:{d['drug']}", f"disease:{DISEASE}", type="ranked_for", confidence=d["score"],
                   direction="increase", n_claims=d["n_claims"], claim_ids=[])
    by_stage: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_path: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in claims:
        by_stage[(c["drug"], c["stage"] or "general")].append(c)
        for name, pat in PATHWAYS.items():
            if re.search(pat, c.get("pathways") or "", re.IGNORECASE):
                by_path[(c["drug"], name)].append(c)
    for (drug, stage), rows in by_stage.items():
        g.add_edge(f"drug:{drug}", f"stage:{stage}", type="affects_stage", **_edge_summary(rows))
    for (drug, path), rows in by_path.items():
        g.add_edge(f"drug:{drug}", f"pathway:{path}", type="engages_pathway", **_edge_summary(rows))
    g.remove_nodes_from([n for n, a in g.nodes(data=True)
                         if a["type"] in ("pathway", "stage") and g.degree(n) == 0])
    return g


def to_json(g: nx.DiGraph) -> dict[str, Any]:
    return {
        "nodes": [{"id": n, **a} for n, a in g.nodes(data=True)],
        "links": [{"source": u, "target": v, **a} for u, v, a in g.edges(data=True)],
    }


def export_graph(g: nx.DiGraph) -> None:
    config.GRAPH_JSON.write_text(json.dumps(to_json(g)), encoding="utf-8")
