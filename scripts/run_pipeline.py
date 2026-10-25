"""Resumable pipeline: ingest -> extract -> grade -> graph -> rank.

Usage: run_pipeline.py [--stage ingest] [--drugs a,b] [--dry-run] [--pubmed-n 40 --fulltext-n 10 --reingest]
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import agents, db, extract, grade, ingest
from app.llm import OllamaLLM
from app.pubmed import PubMedClient
from app.tinyfish_client import TinyFishClient


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "ingest", "extract", "agents", "build"])
    ap.add_argument("--drugs", help="comma-separated subset of seed drugs")
    ap.add_argument("--dry-run", action="store_true", help="TinyFish cache only, no live calls")
    ap.add_argument("--pubmed-n", type=int, default=14, help="PubMed papers per drug (ingest)")
    ap.add_argument("--fulltext-n", type=int, default=4, help="full-text fetches per drug (ingest)")
    ap.add_argument("--reingest", action="store_true", help="clear ingest checkpoints for the selected drugs first")
    args = ap.parse_args()

    drugs = ingest.load_drugs()
    if args.drugs:
        wanted = {d.strip().lower() for d in args.drugs.split(",")}
        drugs = [d for d in drugs if d.name in wanted]
    con = db.connect()
    if args.stage in ("all", "ingest"):
        if args.reingest:
            con.executemany("DELETE FROM checkpoints WHERE stage='ingest' AND key=?", [(d.name,) for d in drugs])
            con.commit()
        ingest.run_ingest(drugs, con, TinyFishClient(dry_run=args.dry_run), PubMedClient(),
                          pubmed_n=args.pubmed_n, fulltext_n=args.fulltext_n)
    if args.stage in ("all", "extract"):
        extract.run_extract(con, drugs, OllamaLLM())
    if args.stage in ("all", "agents"):
        print(agents.run_agents(con, drugs, TinyFishClient(dry_run=args.dry_run)))
    if args.stage in ("all", "build"):
        print(f"[build] graded {grade.grade_all(con)} claims")
        for script in ("validate.py", "export_static.py"):
            subprocess.run([sys.executable, str(Path(__file__).parent / script)], check=True, stdout=subprocess.DEVNULL)
        print("[build] wrote results/validation.*, data/graph.json, frontend/public/data/*")
    n = con.execute("SELECT COUNT(*), SUM(fulltext_available) FROM papers").fetchone()
    print(f"papers={n[0]} fulltext={n[1]}")


if __name__ == "__main__":
    main()
