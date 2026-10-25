"""Blank labelling sheet for a human annotator, plus agreement against the AI labels.

  python scripts/make_human_sheet.py            # writes data/labels/gold_human_blank.csv (sentences only)
  python scripts/make_human_sheet.py --compare data/labels/gold_human.csv   # Cohen kappa vs the AI gold set

The blank sheet has no AI labels, so the annotator is not anchored by them. Fill has_claim (1/0) and, when 1,
direction (increase|decrease|no_effect|mixed), stage (proliferation|survival|differentiation|general),
species (mouse|rat|human|other, only if the sentence says it), study_design (rodent|human_clinical|
human_cells_organoid|review_or_meta|other, only if the sentence says it) and markers.
Rule: has_claim=1 only when the sentence reports this study's own effect of the named drug on neurogenesis,
not a citation of earlier work, a hypothesis, or a different drug.
"""
import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config

LABELS = config.DATA_DIR / "labels"
COLS = ["gold_id", "paper_id", "drug", "sentence", "has_claim", "direction", "stage", "species", "study_design", "markers"]


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(x == "1" for x in a) / n, sum(y == "1" for y in b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", help="human-labelled CSV to compare with the AI gold set")
    args = ap.parse_args()
    ai = {r["gold_id"]: r for r in csv.DictReader(io.StringIO((LABELS / "gold_sentences.csv").read_text(encoding="utf-8")))}
    if not args.compare:
        out = LABELS / "gold_human_blank.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            for r in ai.values():
                w.writerow({c: (r[c] if c in ("gold_id", "paper_id", "drug", "sentence") else "") for c in COLS})
        print(f"wrote {out} ({len(ai)} rows, no labels)")
        return
    human = {r["gold_id"]: r for r in csv.DictReader(io.StringIO(Path(args.compare).read_text(encoding="utf-8")))
             if r["has_claim"].strip() in ("0", "1")}
    ids = [i for i in ai if i in human]
    if not ids:
        sys.exit("no labelled rows in the human file")
    a, h = [ai[i]["has_claim"] for i in ids], [human[i]["has_claim"].strip() for i in ids]
    print(f"rows compared: {len(ids)}; claim-detection agreement {sum(x == y for x, y in zip(a, h, strict=True))}/{len(ids)}; "
          f"Cohen kappa {kappa(a, h):.3f}")
    both = [i for i in ids if ai[i]["has_claim"] == "1" and human[i]["has_claim"].strip() == "1"]
    for f in ("direction", "stage", "species", "study_design"):
        print(f"{f}: agree {sum(ai[i][f].strip().lower() == human[i][f].strip().lower() for i in both)}/{len(both)}")


if __name__ == "__main__":
    main()
