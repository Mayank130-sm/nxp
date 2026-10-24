"""PubMed E-utilities (esearch + efetch) with polite rate limiting and disk cache."""
from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import config

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class PubMedRecord:
    pmid: str
    title: str
    abstract: str
    year: int | None
    doi: str | None
    pmcid: str | None


class PubMedClient:
    def __init__(self, cache_dir: Path | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.cache_dir = cache_dir or config.CACHE_DIR / "pubmed"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._http = httpx.Client(transport=transport, timeout=60.0)
        # NCBI allows 3 req/s without a key, 10 with one.
        self._min_gap = 0.11 if config.NCBI_API_KEY else 0.36
        self._last = 0.0

    def _get(self, endpoint: str, params: dict) -> str:
        params = {**params, "tool": "neurorx", "email": config.NCBI_EMAIL}
        if config.NCBI_API_KEY:
            params["api_key"] = config.NCBI_API_KEY
        key = hashlib.sha256(f"{endpoint}{sorted(params.items())}".encode()).hexdigest()[:32]
        path = self.cache_dir / f"{key}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        for attempt in range(4):
            wait = self._min_gap - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            resp = self._http.get(f"{BASE}/{endpoint}", params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            path.write_text(resp.text, encoding="utf-8")
            return resp.text
        raise RuntimeError(f"PubMed {endpoint} failed after retries")

    def esearch(self, term: str, retmax: int = 20) -> list[str]:
        text = self._get("esearch.fcgi", {"db": "pubmed", "term": term, "retmax": retmax, "retmode": "xml",
                                          "sort": "relevance"})
        return [e.text for e in ET.fromstring(text).findall(".//IdList/Id") if e.text]

    def efetch(self, pmids: list[str]) -> list[PubMedRecord]:
        if not pmids:
            return []
        text = self._get("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
        return parse_efetch(text)


def parse_efetch(xml_text: str) -> list[PubMedRecord]:
    out: list[PubMedRecord] = []
    for art in ET.fromstring(xml_text).findall(".//PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID") or ""
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            body = "".join(ab.itertext())
            parts.append(f"{label}: {body}" if label else body)
        year_txt = art.findtext(".//JournalIssue/PubDate/Year") or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
        doi = pmcid = None
        for aid in art.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text
            elif aid.get("IdType") == "pmc":
                pmcid = aid.text
        if pmid and title:
            out.append(PubMedRecord(pmid, title.strip(), "\n".join(parts).strip(),
                                    int(year_txt) if year_txt.isdigit() else None, doi, pmcid))
    return out
