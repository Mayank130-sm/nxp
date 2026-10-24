import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db
from app.grade import detect_conflicts, grade_all, grade_claim, marker_score, replication_score
from app.rank import noisy_or, rank_drugs


def claim(**kw):
    base = {"id": 1, "paper_id": 1, "drug": "fluoxetine", "stage": "proliferation", "direction": "increase",
            "species": "mouse", "study_design": "rodent", "markers": "BrdU, DCX, NeuN", "dose": "10 mg/kg",
            "quote_verified": 1, "pathways": None}
    return {**base, **kw}


def test_weights_sum_to_100():
    assert sum(config.WEIGHTS.values()) == 100


def test_marker_and_replication_math():
    assert marker_score("BrdU, DCX, NeuN") == 1.0
    assert marker_score("BrdU") == 1 / 3
    assert marker_score(None) == 0.0
    assert [replication_score(n) for n in (0, 1, 2, 5)] == [0.0, 0.2, 0.6, 1.0]


def test_grade_claim_components_and_penalties():
    g = grade_claim(claim(), n_papers=3, in_conflict=False, bbb_note="Crosses the blood-brain barrier")
    assert g["parts"] == {"replication": 25.0, "design": 15.0, "markers": 20.0, "species": 12.0, "dose": 10.0}
    assert g["confidence"] == 82.0 and g["penalties"] == {}
    weak = grade_claim(claim(markers=None, dose=None, species=None, study_design=None), 1, True)
    assert weak["penalties"] == {"single_lab": 10, "contradiction": 15}
    assert weak["confidence"] < 25
    assert grade_claim(claim(quote_verified=0), 3, False)["penalties"]["unverified_quote"] == 50


def test_conflict_detection_side_by_side():
    claims = [claim(id=1, direction="increase"), claim(id=2, paper_id=2, direction="decrease"),
              claim(id=3, paper_id=3, stage="survival", direction="increase")]
    [c] = detect_conflicts(claims)
    assert (c["drug"], c["stage"], c["severity"]) == ("fluoxetine", "proliferation", "strong")
    assert set(c["sides"]) == {"increase", "decrease"}
    assert detect_conflicts([claim(quote_verified=0, direction="decrease"), claim()]) == []
    weak = detect_conflicts([claim(), claim(id=2, paper_id=2, direction="no_effect")])
    assert weak[0]["severity"] == "weak"


def test_noisy_or():
    assert noisy_or([]) == 0.0
    assert abs(noisy_or([50, 50]) - 0.75) < 1e-9


def test_rank_flags_suppressors_and_orders():
    claims = []
    for i, (drug, direction, conf) in enumerate(
            [("fluoxetine", "increase", 70), ("fluoxetine", "increase", 60), ("ethanol", "decrease", 65)]):
        claims.append(claim(id=i, paper_id=i, drug=drug, direction=direction, confidence=conf, replication=10,
                            g_design=10, g_markers=10, g_species=10, g_dose=5, pathways="BDNF"))
    ranked = rank_drugs(claims, {"fluoxetine": "control_pos", "ethanol": "control_neg", "x": "candidate"})
    assert ranked[0]["drug"] == "fluoxetine" and ranked[0]["pathways"] == ["BDNF/TrkB"]
    eth = next(d for d in ranked if d["drug"] == "ethanol")
    assert eth["safety_flag"] and eth["score"] == 0.0
    assert "SAFETY FLAG" in eth["why"] and "not a treatment claim" in eth["why"]
    abl = rank_drugs(claims, {"fluoxetine": "control_pos"}, graded=False)
    assert abl[0]["drug"] == "fluoxetine"


def test_grade_all_end_to_end(tmp_path):
    con = db.connect(tmp_path / "t.db")
    for pid in (1, 2):
        con.execute("INSERT INTO claims(paper_id,drug,stage,direction,species,study_design,markers,quote_verified)"
                    " VALUES (?,?,?,?,?,?,?,1)", (pid, "lithium", "survival", "increase", "mouse", "rodent", "BrdU"))
    assert grade_all(con) == 2
    rows = con.execute("SELECT confidence, penalties FROM claim_scores").fetchall()
    assert len(rows) == 2 and all(r["confidence"] > 0 and "single_lab" not in r["penalties"] for r in rows)
