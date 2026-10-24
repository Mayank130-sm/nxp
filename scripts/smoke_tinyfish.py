"""P0 smoke test: one real Search, one real Fetch, one real Agent goal."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.tinyfish_client import TinyFishClient

tf = TinyFishClient()

print("== SEARCH ==")
s = tf.search("fluoxetine adult hippocampal neurogenesis DCX BrdU")
print(f"total_results={s.get('total_results')} returned={len(s.get('results', []))}")
for r in s.get("results", [])[:5]:
    print(f"- {r.get('title')} | {r.get('url')}")

urls = [r["url"] for r in s.get("results", []) if r.get("url")][:1]
print("\n== FETCH ==")
if urls:
    f = tf.fetch(urls)
    for r in f.get("results", []):
        print(f"{r['url']} -> {len(r.get('text') or '')} chars, title={r.get('title')}")
    print("errors:", f.get("errors"))

print("\n== AGENT ==")
a = tf.run_agent(
    "https://clinicaltrials.gov",
    "Search for trials of metformin in Alzheimer's disease. Return JSON list of up to 3 trials with nct_id, phase, status.",
    output_schema={
        "type": "object",
        "properties": {"trials": {"type": "array", "items": {"type": "object", "properties": {
            "nct_id": {"type": "string"}, "phase": {"type": "string"}, "status": {"type": "string"}}}}},
    },
)
print(json.dumps({k: a.get(k) for k in ("run_id", "status", "num_of_steps", "result", "error")}, indent=2))
