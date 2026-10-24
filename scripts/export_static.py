"""Write the API responses as static JSON into frontend/public/data/ (frontend falls back to these)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db, graph, service
from app.rank import load_graded

OUT = config.ROOT / "frontend" / "public" / "data"


def dump(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, default=str), encoding="utf-8")


def main() -> None:
    con = db.connect()
    ranked = service.ranked_list(con)
    dump(OUT / "drugs.json", ranked)
    for d in ranked:
        detail = service.drug_detail(con, d["drug"])
        dump(OUT / "drug" / f"{d['drug'].replace(' ', '_')}.json", detail)
    dump(OUT / "graph.json", service.graph_json(con))
    dump(OUT / "stats.json", service.stats(con))
    graph.export_graph(graph.build_graph(load_graded(con), ranked))
    print(f"exported {len(ranked)} drugs to {OUT}")


if __name__ == "__main__":
    main()
