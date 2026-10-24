import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extract import build_windows, extract_window, norm_ws, validate_claim, verify_quote
from app.models import Drug

FLX = Drug(name="fluoxetine", synonyms=["Prozac"], category="control_pos")
TEXT = (
    "Mice were housed in groups of five. "
    "Chronic fluoxetine  treatment increased the number of BrdU+ cells in the dentate gyrus. "
    "The weather was fine that day in the lab. "
    "Prozac did not alter DCX expression in the subventricular zone of old rats."
)


def test_norm_and_verify_quote():
    assert norm_ws("a \n  b") == "a b"
    assert verify_quote("Chronic fluoxetine treatment increased the number of BrdU+ cells", TEXT)
    assert not verify_quote("Fluoxetine cured everything in the hippocampus", TEXT)
    assert not verify_quote("too short", "too short")
    assert not verify_quote(None, TEXT)


def test_gate_requires_drug_and_neuro_vocab():
    windows = build_windows(TEXT, FLX)
    assert any("BrdU" in w for w in windows)
    assert any("Prozac" in w for w in windows)  # synonym matches
    assert not any("weather" in w and "BrdU" not in w and "Prozac" not in w for w in windows)
    assert build_windows("Metformin increased proliferation of neural stem cells in vitro.", FLX) == []


def test_validate_rejects_unverified_and_no_claim():
    window = "Chronic fluoxetine treatment increased the number of BrdU+ cells in the dentate gyrus."
    good = {"has_claim": True, "direction": "increase", "stage": "proliferation", "markers": ["BrdU"],
            "evidence_quote": "fluoxetine treatment increased the number of BrdU+ cells"}
    claim = validate_claim(good, window, FLX)
    assert claim and claim["quote_verified"] == 1 and claim["markers"] == "BrdU"
    assert validate_claim({**good, "evidence_quote": "fluoxetine made new neurons appear everywhere"}, window, FLX) is None
    assert validate_claim({**good, "has_claim": False}, window, FLX) is None
    assert validate_claim({**good, "direction": None}, window, FLX) is None


class FakeLLM:
    model = "fake"

    def __init__(self, out):
        self.out = out

    def complete_json(self, system, prompt, schema):
        if isinstance(self.out, Exception):
            raise self.out
        return self.out


def test_extract_window_survives_llm_errors():
    assert extract_window(FakeLLM(ValueError("bad json")), FLX, "x") is None


def test_claim_context_is_conservative():
    from app.extract import claim_context
    # species stated in the quote wins
    assert claim_context("Sildenafil raised BrdU+ cells in rats.", "Patients were treated. Mice mice.", "A study") == {
        "species": "rat", "study_design": "rodent"}
    # paper-level fallback is animal-only: many mentions of patients must NOT yield human evidence
    ctx = claim_context("Neurogenesis increased.", "Patients patients patients. Mice were dosed. Mice were scored.", "A study")
    assert ctx == {"species": "mouse", "study_design": "rodent"}
    ctx = claim_context("Neurogenesis increased.", "Patients patients patients.", "A study")
    assert ctx == {"species": None, "study_design": None}
    # human only when the quote says so
    assert claim_context("Patients on the drug showed more DCX cells.", "x", "Randomized trial")["study_design"] == "human_clinical"
    assert claim_context("x", "y", "Sildenafil: recent pharmacological applications")["study_design"] == "review_or_meta"
