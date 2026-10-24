"""Print (and save to results/slide_numbers.md) the headline numbers for the slides, from real data."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db
from app.tinyfish_client import usage_summary


def main() -> None:
    con = db.connect()
    one = lambda sql: con.execute(sql).fetchone()[0]
    val = json.loads((config.RESULTS_DIR / "validation.json").read_text(encoding="utf-8"))
    ev_path = config.RESULTS_DIR / "extraction_eval.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None
    usage = usage_summary()
    live = {k: v["live"] for k, v in usage.items()}
    frac = val["quote_verified_fraction"]
    rows = [
        ("Papers processed", f"{one('SELECT COUNT(*) FROM papers')} ({one('SELECT SUM(fulltext_available) FROM papers')} with full text)"),
        ("Claims verified (exact-quote grounded)", str(one("SELECT COUNT(*) FROM claims WHERE quote_verified=1"))),
        ("Controls recovered", f"{val['recovered']} of {val['total']}"),
        ("TinyFish live calls", f"{sum(live.values())} (search {live.get('search', 0)}, fetch {live.get('fetch', 0)}, agent {live.get('agent', 0)})"),
        ("Extraction claim-detection precision / recall (AI-labelled gold set)", f"{ev['claim_detection']['precision']:.0%} / {ev['claim_detection']['recall']:.0%} on n={ev['n_gold']}" if ev else "pending"),
        ("LLM claims whose quote verified", f"{frac:.1%}" if frac is not None else "unknown"),
        ("Extractor model", config.OLLAMA_MODEL),
    ]
    text = "# Numbers for the slides\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in rows) + "\n"
    (config.RESULTS_DIR / "slide_numbers.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
