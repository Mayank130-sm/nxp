import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, ingest
from app.pubmed import parse_efetch

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
<Journal><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>Fluoxetine boosts <i>neurogenesis</i></ArticleTitle>
<Abstract><AbstractText Label="RESULTS">BrdU+ cells increased.</AbstractText></Abstract>
</Article></MedlineCitation><PubmedData><ArticleIdList>
<ArticleId IdType="doi">10.1/ABC</ArticleId><ArticleId IdType="pmc">PMC99</ArticleId>
</ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""


def test_parse_efetch():
    [r] = parse_efetch(XML)
    assert (r.pmid, r.year, r.doi, r.pmcid) == ("123", 2020, "10.1/ABC", "PMC99")
    assert r.title == "Fluoxetine boosts neurogenesis"
    assert r.abstract == "RESULTS: BrdU+ cells increased."


def test_upsert_dedupes_by_pmid_doi_title(tmp_path):
    con = db.connect(tmp_path / "t.db")
    a = ingest.upsert_paper(con, title="A Study of X", pmid="1", doi="10.1/X")
    assert ingest.upsert_paper(con, title="different", pmid="1") == a
    assert ingest.upsert_paper(con, title="other", doi="10.1/x") == a
    assert ingest.upsert_paper(con, title="a study of x!") == a
    assert ingest.upsert_paper(con, title="Something else") != a


def test_keep_sections_drops_references():
    md = "intro " * 10 + "\n## Methods\n" + "mice were dosed. " * 120 + "\n## References\n1. junk ref"
    out = ingest.keep_sections(md)
    assert "mice were dosed" in out and "junk ref" not in out


def test_resume_checkpoint(tmp_path):
    con = db.connect(tmp_path / "t.db")
    assert not db.is_done(con, "ingest", "fluoxetine")
    db.mark_done(con, "ingest", "fluoxetine")
    assert db.is_done(con, "ingest", "fluoxetine")
