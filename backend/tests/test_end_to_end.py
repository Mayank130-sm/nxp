import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, extract, grade, service
from app.graph import build_graph, to_json
from app.ingest import load_drugs
from app.rank import load_graded, rank_drugs

PAPERS = [  # (drug, text, llm direction)
    ("fluoxetine", "Chronic fluoxetine treatment increased the number of BrdU+ and DCX+ cells in the dentate gyrus of adult mice.", "increase"),
    ("fluoxetine", "Fluoxetine increased proliferation of neural progenitors in the dentate gyrus of rats, measured by Ki67 and NeuN.", "increase"),
    ("fluoxetine", "Fluoxetine reduced BrdU+ cell survival in the dentate gyrus of stressed mice at high dose.", "decrease"),
    ("ethanol", "Chronic ethanol exposure decreased neurogenesis and BrdU+ cell counts in the dentate gyrus of adult rats.", "decrease"),
    ("lithium", "Lithium enhanced neural stem cell proliferation via Wnt signalling, increasing Ki67 and DCX cells in mice.", "increase"),
]


class FixtureLLM:
    """Gate says yes; extraction echoes the first sentence as a verbatim quote."""
    model = "fixture"

    def __init__(self, text_to_dir):
        self.dirs = text_to_dir

    def complete_json(self, system, prompt, schema):
        if "reports_effect" in schema["properties"]:
            return {"reports_effect": True}
        text = prompt.split("TEXT:\n", 1)[1]
        drug = prompt.split("DRUG: ", 1)[1].split("\n", 1)[0]
        quote, direction = next((t, d) for dr, t, d in PAPERS if dr == drug and t in text)
        return {"has_claim": True, "drug": drug, "stage": "proliferation", "direction": direction,
                "markers": ["BrdU", "DCX"], "pathways": ["Wnt"] if drug == "lithium" else [],
                "evidence_quote": quote, "confidence_raw": 0.9}


def build_db(tmp_path):
    con = db.connect(tmp_path / "e2e.db")
    for i, (drug, text, _) in enumerate(PAPERS, 1):
        path = tmp_path / f"{i}.txt"
        path.write_text(f"Title {i}\n\nABSTRACT\n{text}", encoding="utf-8")
        con.execute("INSERT INTO papers(id,pmid,title,text_path,year) VALUES (?,?,?,?,2020)", (i, str(100 + i), f"Title {i}", str(path)))
        con.execute("INSERT INTO paper_drugs VALUES (?,?)", (i, drug))
    con.commit()
    return con


def test_pipeline_end_to_end(tmp_path, monkeypatch):
    con = build_db(tmp_path)
    drugs = [d for d in load_drugs() if d.name in {"fluoxetine", "ethanol", "lithium"}]
    extract.run_extract(con, drugs, FixtureLLM({}))
    assert con.execute("SELECT COUNT(*) FROM claims WHERE quote_verified=1").fetchone()[0] == 5
    stats = con.execute("SELECT SUM(proposed), SUM(quote_failed) FROM extract_stats").fetchone()
    assert (stats[0], stats[1]) == (5, 0)

    assert grade.grade_all(con) == 5
    claims = load_graded(con)
    ranked = rank_drugs(claims, {d.name: d.category for d in drugs})
    by = {d["drug"]: d for d in ranked}
    assert by["fluoxetine"]["n_conflicts"] == 1 and by["fluoxetine"]["n_pro"] == 2
    assert by["ethanol"]["safety_flag"] and by["ethanol"]["score"] == 0
    assert by["lithium"]["pathways"] == ["Wnt/beta-catenin"]
    assert by["lithium"]["score"] > by["ethanol"]["score"]

    graph = to_json(build_graph(claims, ranked))
    types = {n["type"] for n in graph["nodes"]}
    assert {"drug", "stage", "disease", "pathway"} <= types
    assert any(link["type"] == "engages_pathway" for link in graph["links"])

    monkeypatch.setattr(service, "categories", lambda: {d.name: d.category for d in drugs})
    detail = service.drug_detail(con, "fluoxetine")
    assert detail["conflicts"][0]["severity"] == "strong"
    assert all(c["pmid"] and c["evidence_quote"] for c in detail["claims"])
    assert "not a treatment claim" in detail["disclaimer"]
    assert service.drug_detail(con, "nonexistent") is None


def test_fabricated_quote_is_discarded(tmp_path):
    con = build_db(tmp_path)

    class Liar(FixtureLLM):
        def complete_json(self, system, prompt, schema):
            out = super().complete_json(system, prompt, schema)
            if "has_claim" in out:
                out["evidence_quote"] = "Fluoxetine cured every neuron in the whole brain overnight."
            return out

    drugs = [d for d in load_drugs() if d.name == "fluoxetine"]
    extract.run_extract(con, drugs, Liar({}))
    assert con.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0
    assert con.execute("SELECT SUM(quote_failed) FROM extract_stats").fetchone()[0] == 3
