"""Write data/labels/gold_sentences.csv: ~100 gated sentence windows for hand labelling.

Fill the blank label columns (has_claim = 1/0; direction/stage/species/study_design/markers when 1).
"""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db, ingest
from app.extract import build_windows

N = 100
FIELDS = ["gold_id", "paper_id", "drug", "sentence", "has_claim", "direction", "stage", "species",
          "study_design", "markers"]


def main() -> None:
    random.seed(7)
    con = db.connect()
    drugs = {d.name: d for d in ingest.load_drugs()}
    pool = []
    for r in con.execute("SELECT p.id, p.text_path, pd.drug FROM papers p JOIN paper_drugs pd "
                         "ON pd.paper_id=p.id WHERE p.text_path IS NOT NULL"):
        text = (config.ROOT / r["text_path"]).read_text(encoding="utf-8")
        for w in build_windows(text, drugs[r["drug"]], max_windows=3):
            pool.append((r["id"], r["drug"], w))
    random.shuffle(pool)
    out = config.DATA_DIR / "labels" / "gold_sentences.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(FIELDS)
        for i, (pid, drug, w) in enumerate(pool[:N], 1):
            wr.writerow([i, pid, drug, w, "", "", "", "", "", ""])
    print(f"wrote {min(N, len(pool))} rows to {out}")


if __name__ == "__main__":
    main()
