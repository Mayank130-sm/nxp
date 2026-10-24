"""Pydantic schemas shared by the pipeline and API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Stage = Literal["proliferation", "survival", "differentiation", "general"]
Direction = Literal["increase", "decrease", "no_effect", "mixed"]
StudyDesign = Literal[
    "in_vitro", "rodent", "nonhuman_primate", "human_cells_organoid", "human_clinical", "review_or_meta"
]


class Drug(BaseModel):
    name: str
    synonyms: list[str]
    category: Literal["control_pos", "control_neg", "candidate"]


class Paper(BaseModel):
    id: int | None = None
    pmid: str | None = None
    doi: str | None = None
    title: str
    year: int | None = None
    source_url: str | None = None
    fetched_at: str | None = None
    fulltext_available: bool = False
    text_path: str | None = None
