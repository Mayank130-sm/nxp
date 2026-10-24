"""FastAPI app: ranked drugs, drug detail, graph, stats."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, service

app = FastAPI(title="NeuroRx", description="Evidence-graded drug repurposing graph for neurogenesis in AD")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/drugs")
def drugs() -> list[dict[str, Any]]:
    return service.ranked_list(db.connect())


@app.get("/drugs/{name}")
def drug(name: str) -> dict[str, Any]:
    detail = service.drug_detail(db.connect(), name.lower())
    if detail is None:
        raise HTTPException(404, f"Unknown drug: {name}")
    return detail


@app.get("/graph")
def graph() -> dict[str, Any]:
    return service.graph_json(db.connect())


@app.get("/stats")
def stats() -> dict[str, Any]:
    return service.stats(db.connect())
