"""Per-field precision / recall / F1 of extracted claims against data/labels/gold_sentences.csv.

A predicted claim is matched to a gold row when it has the same paper_id and drug and its evidence
quote lies inside the gold sentence window. Has-claim is scored as a detection task; every other
field is scored only on rows where both sides state a value.
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db
from app.extract import norm_ws

FIELDS = ["direction", "stage", "species", "study_design"]


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(config.DATA_DIR / "labels" / "gold_sentences.csv"),
                    help="labelled CSV (default: the AI-made gold set; pass the human-labelled file when you have it)")
    ap.add_argument("--out", default=str(config.RESULTS_DIR / "extraction_eval.json"))
    args = ap.parse_args()
    gold = [r for r in csv.DictReader(io.StringIO(Path(args.gold).read_text(encoding="utf-8")))
            if r["has_claim"].strip() in ("0", "1")]
    if not gold:
        sys.exit("No labelled rows yet: fill has_claim (1/0) in data/labels/gold_sentences.csv")
    con = db.connect()
    claims = con.execute("SELECT * FROM claims WHERE quote_verified=1").fetchall()

    def match(g: dict) -> dict | None:
        win = norm_ws(g["sentence"])
        for c in claims:
            if str(c["paper_id"]) == g["paper_id"] and c["drug"] == g["drug"] and c["evidence_quote"] in win:
                return dict(c)
        return None

    tp = fp = fn = 0
    counts = {f: [0, 0, 0] for f in FIELDS}  # tp, fp, fn
    for g in gold:
        pred, truth = match(g), g["has_claim"].strip() == "1"
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif truth and not pred:
            fn += 1
        if pred and truth:
            for f in FIELDS:
                gv, pv = (g[f] or "").strip().lower(), (pred.get(f) or "").strip().lower()
                if gv and pv:
                    counts[f][0 if gv == pv else 1] += 1
                    if gv != pv:
                        counts[f][2] += 1
                elif gv and not pv:
                    counts[f][2] += 1
                elif pv and not gv:
                    counts[f][1] += 1
    report = {"claim_detection": prf(tp, fp, fn), "n_gold": len(gold)}
    report.update({f: prf(*counts[f]) for f in FIELDS})
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
