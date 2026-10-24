"""P5 validation: control recovery, ranking ablation (with vs. without grading), quote-verified fraction.

Writes results/validation.json (exposed via /stats) and results/validation.md. Numbers come straight from the
database; if the pipeline disagrees with a control it is reported as a mismatch, not tuned away.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db, grade, service

POSITIVE = ["fluoxetine", "lithium", "metformin", "memantine"]
NEGATIVE = ["dexamethasone", "morphine", "ethanol"]


def avg_ranks(ranked: list[dict]) -> dict[str, float]:
    """Mean rank with ties averaged, so an ungraded vote count is not rewarded for alphabetical luck."""
    scores = [d["score"] for d in ranked]
    return {d["drug"]: 1 + sum(s > d["score"] for s in scores) + (sum(s == d["score"] for s in scores) - 1) / 2
            for d in ranked}


def control_row(d: dict, kind: str) -> dict:
    if d["n_claims"] == 0:
        observed, ok = "no verified evidence (unknown)", False
    elif kind == "positive":
        ok = d["n_pro"] > d["n_anti"] and not d["safety_flag"]
        observed = f"{d['n_pro']} papers increase / {d['n_anti']} decrease"
    else:
        ok = d["safety_flag"] or d["n_anti"] > d["n_pro"]
        observed = f"{d['n_pro']} papers increase / {d['n_anti']} decrease" + (", safety flag" if d["safety_flag"] else "")
    expected = "pro-neurogenic evidence" if kind == "positive" else "suppression / safety flag"
    return {"drug": d["drug"], "kind": kind, "expected": expected, "observed": observed, "ok": ok,
            "score": d["score"], "rank": d["rank"]}


def main() -> None:
    con = db.connect()
    grade.grade_all(con)
    graded, ungraded = service.ranked_list(con, True), service.ranked_list(con, False)
    by_name = {d["drug"]: d for d in graded}
    controls = [control_row(by_name[n], "positive") for n in POSITIVE] + [control_row(by_name[n], "negative") for n in NEGATIVE]

    ablation = []
    for label, ranked in (("With evidence grading", graded), ("Without grading (vote count)", ungraded)):
        r = avg_ranks(ranked)
        pos, neg = sum(r[n] for n in POSITIVE) / len(POSITIVE), sum(r[n] for n in NEGATIVE) / len(NEGATIVE)
        ablation.append({"label": label, "positives_mean_rank": round(pos, 2), "negatives_mean_rank": round(neg, 2),
                         "separation": round(neg - pos, 2)})

    tot = con.execute("SELECT COALESCE(SUM(proposed),0), COALESCE(SUM(quote_failed),0) FROM extract_stats").fetchone()
    proposed, failed = tot[0], tot[1]
    verified_n = con.execute("SELECT COUNT(*) FROM claims WHERE quote_verified=1").fetchone()[0]
    out = {
        "controls": controls, "recovered": sum(c["ok"] for c in controls), "total": len(controls),
        "quote_verified_fraction": round((proposed - failed) / proposed, 3) if proposed else None,
        "claims_proposed_by_llm": proposed, "claims_quote_failed": failed, "claims_kept": verified_n,
        "ablation": ablation,
    }
    config.RESULTS_DIR.mkdir(exist_ok=True)
    (config.RESULTS_DIR / "validation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = ["# NeuroRx validation", "", "All numbers are computed from the database by `scripts/validate.py`.", "",
             f"## Control recovery: {out['recovered']}/{out['total']}", "",
             "| Drug | Kind | Expected | Observed | Score | Match |", "|---|---|---|---|---|---|"]
    lines += [f"| {c['drug']} | {c['kind']} | {c['expected']} | {c['observed']} | {c['score']:.0f} | {'yes' if c['ok'] else 'NO'} |"
              for c in controls]
    lines += ["", "## Ablation: ranking with vs. without evidence grading", "",
              "Separation = mean rank of negative controls minus mean rank of positive controls (higher is better).", "",
              "| Method | Positives mean rank | Negatives mean rank | Separation |", "|---|---|---|---|"]
    lines += [f"| {a['label']} | {a['positives_mean_rank']} | {a['negatives_mean_rank']} | {a['separation']} |" for a in ablation]
    frac = out["quote_verified_fraction"]
    lines += ["", "## Quote grounding", "",
              f"- Claims proposed by the LLM: {proposed}", f"- Rejected (quote not an exact substring): {failed}",
              f"- Fraction with verified quote at proposal time: {frac if frac is not None else 'unknown'}",
              f"- Claims kept after de-duplication: {verified_n}", ""]
    ev = config.RESULTS_DIR / "extraction_eval.json"
    lines += ["## Extraction vs. gold set", ""]
    lines += ["```json", ev.read_text(encoding="utf-8"), "```"] if ev.exists() else [
        "Not computed: `data/labels/gold_sentences.csv` has not been hand-labelled yet."]
    (config.RESULTS_DIR / "validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
