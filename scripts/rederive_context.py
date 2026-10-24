"""Re-derive species / study_design for all existing claims with the claim_context rules.

Deterministic, no LLM: species comes from the claim's own quote, else the dominant animal species of the
paper; human is assigned only when the quote says so; review-style titles are labelled as reviews.
A fresh `run_pipeline.py --stage extract` already applies claim_context directly, so this script only
brings claims extracted before the rule change in line with it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db
from app.extract import claim_context


def main() -> None:
    con = db.connect()
    changed = 0
    rows = con.execute("SELECT c.id, c.species, c.study_design, c.evidence_quote, p.text_path FROM claims c "
                       "JOIN papers p ON p.id=c.paper_id").fetchall()
    for r in rows:
        text = (config.ROOT / r["text_path"]).read_text(encoding="utf-8")
        new = claim_context(r["evidence_quote"], text, text.split("\n", 1)[0])
        if (new["species"], new["study_design"]) != (r["species"], r["study_design"]):
            con.execute("UPDATE claims SET species=?, study_design=? WHERE id=?",
                        (new["species"], new["study_design"], r["id"]))
            changed += 1
    con.commit()
    print(f"re-derived context for {changed} of {len(rows)} claims")
    for row in con.execute("SELECT study_design, species, COUNT(*) n FROM claims GROUP BY 1,2 ORDER BY 3 DESC"):
        print(tuple(row))


if __name__ == "__main__":
    main()
