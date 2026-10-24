"""Ingestion: seed drugs -> PubMed abstracts + TinyFish Search/Fetch -> cached papers in SQLite."""
from __future__ import annotations

import csv
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

from . import config, db
from .models import Drug
from .pubmed import PubMedClient, PubMedRecord
from .tinyfish_client import TinyFishClient

TEXT_DIR = config.CACHE_DIR / "texts"
OA_HOSTS = ("pmc.ncbi.nlm.nih.gov", "europepmc.org", "biorxiv.org", "medrxiv.org")
NEURO_TERMS = '(neurogenesis OR "neural stem cell" OR "neural progenitor" OR "dentate gyrus" OR "subventricular zone")'
SEARCH_TEMPLATES = (
    "{d} adult hippocampal neurogenesis DCX BrdU",
    "{d} neural stem cell proliferation Alzheimer",
    "{d} neurogenesis impairment",
)
KEEP_HEADING = re.compile(r"abstract|method|result|materials|experimental|summary", re.IGNORECASE)
DROP_HEADING = re.compile(r"reference|acknowledg|funding|conflict|author contrib", re.IGNORECASE)
MAX_CHARS = 60_000


def load_drugs(path: Path | None = None) -> list[Drug]:
    with (path or config.DATA_DIR / "seed_drugs.csv").open(encoding="utf-8") as fh:
        return [
            Drug(name=r["drug"], synonyms=[s for s in r["synonyms"].split(";") if s], category=r["category"])
            for r in csv.DictReader(fh)
        ]


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())[:120]


def keep_sections(markdown: str) -> str:
    """Keep Abstract/Methods/Results-type sections of a markdown article; drop references etc."""
    blocks = re.split(r"(?m)^(#{1,4}\s.*)$", markdown)
    kept, keeping = [blocks[0][:3000]], False
    for i in range(1, len(blocks), 2):
        heading, body = blocks[i], blocks[i + 1] if i + 1 < len(blocks) else ""
        if DROP_HEADING.search(heading):
            keeping = False
        elif KEEP_HEADING.search(heading):
            keeping = True
        if keeping:
            kept.append(f"{heading}\n{body}")
    text = "\n".join(kept).strip()
    if len(text) < 1500:  # headings not recognised; fall back to the page start
        text = markdown
    return text[:MAX_CHARS]


def upsert_paper(con: sqlite3.Connection, *, title: str, pmid: str | None = None, doi: str | None = None,
                 year: int | None = None, url: str | None = None) -> int:
    """Insert a paper, merging by PMID, then DOI, then normalised title."""
    key = title_key(title)
    doi = doi.lower() if doi else None
    row = None
    if pmid:
        row = con.execute("SELECT id FROM papers WHERE pmid=?", (pmid,)).fetchone()
    if row is None and doi:
        row = con.execute("SELECT id FROM papers WHERE doi=?", (doi,)).fetchone()
    if row is None and key:
        row = con.execute("SELECT id FROM papers WHERE title_key=?", (key,)).fetchone()
    if row:
        con.execute("UPDATE papers SET pmid=COALESCE(pmid,?), doi=COALESCE(doi,?), year=COALESCE(year,?), "
                    "source_url=COALESCE(source_url,?) WHERE id=?", (pmid, doi, year, url, row["id"]))
        return row["id"]
    cur = con.execute("INSERT INTO papers(pmid,doi,title,title_key,year,source_url) VALUES (?,?,?,?,?,?)",
                      (pmid, doi, title, key, year, url))
    return cur.lastrowid


def save_text(con: sqlite3.Connection, paper_id: int, text: str, url: str, fulltext: bool) -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    path = TEXT_DIR / f"{paper_id}.txt"
    already_full = con.execute("SELECT fulltext_available FROM papers WHERE id=?", (paper_id,)).fetchone()[0]
    if already_full and not fulltext:
        return  # never downgrade full text to an abstract
    path.write_text(text, encoding="utf-8")
    con.execute("UPDATE papers SET text_path=?, fetched_at=?, fulltext_available=?, source_url=? WHERE id=?",
                (str(path.relative_to(config.ROOT)), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 int(fulltext), url, paper_id))


def pubmed_query(drug: Drug) -> str:
    names = " OR ".join(f'"{n}"[Title/Abstract]' for n in [drug.name, *drug.synonyms[:2]])
    return f"({names}) AND {NEURO_TERMS}"


def ingest_drug(con: sqlite3.Connection, drug: Drug, tf: TinyFishClient, pm: PubMedClient,
                pubmed_n: int = 14, fulltext_n: int = 4) -> dict[str, int]:
    stats = {"pubmed": 0, "search_urls": 0, "fulltext": 0}
    records: list[PubMedRecord] = pm.efetch(pm.esearch(pubmed_query(drug), retmax=pubmed_n))
    for r in records:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{r.pmid}/"
        pid = upsert_paper(con, title=r.title, pmid=r.pmid, doi=r.doi, year=r.year, url=url)
        con.execute("INSERT OR IGNORE INTO paper_drugs VALUES (?,?)", (pid, drug.name))
        if r.abstract:
            save_text(con, pid, f"{r.title}\n\nABSTRACT\n{r.abstract}", url, False)
        stats["pubmed"] += 1

    # TinyFish Search: collect ranked URLs, keep open-access hosts
    oa_urls: list[str] = []
    for tmpl in SEARCH_TEMPLATES:
        for hit in tf.search(tmpl.format(d=drug.name)).get("results", []):
            url = hit.get("url", "")
            stats["search_urls"] += 1
            if urlparse(url).netloc in OA_HOSTS and url not in oa_urls:
                oa_urls.append(url)
    # plus PMC full text for PubMed records that have a PMCID
    pmc_urls = [f"https://pmc.ncbi.nlm.nih.gov/articles/{r.pmcid}/" for r in records if r.pmcid]
    targets = list(dict.fromkeys(oa_urls + pmc_urls))[:fulltext_n]
    for i in range(0, len(targets), config.FETCH_BATCH_MAX):
        for page in tf.fetch(targets[i:i + config.FETCH_BATCH_MAX]).get("results", []):
            text, title = page.get("text") or "", page.get("title") or ""
            if len(text) < 1500 or not title:
                continue
            url = page.get("final_url") or page["url"]
            pid = upsert_paper(con, title=title, url=url)
            con.execute("INSERT OR IGNORE INTO paper_drugs VALUES (?,?)", (pid, drug.name))
            save_text(con, pid, keep_sections(text), url, True)
            stats["fulltext"] += 1
    con.commit()
    return stats


def run_ingest(drugs: list[Drug], con: sqlite3.Connection, tf: TinyFishClient, pm: PubMedClient,
               **kw: int) -> None:
    for drug in drugs:
        if db.is_done(con, "ingest", drug.name):
            print(f"[ingest] {drug.name}: already done, skipping")
            continue
        try:
            stats = ingest_drug(con, drug, tf, pm, **kw)
        except KeyboardInterrupt:
            print("\n[ingest] interrupted; progress saved, rerun to resume")
            raise
        db.mark_done(con, "ingest", drug.name)
        print(f"[ingest] {drug.name}: {stats}")
