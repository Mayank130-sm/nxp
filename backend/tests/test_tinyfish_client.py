import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tinyfish_client import CacheMiss, TinyFishClient, usage_summary


def make_client(tmp_path, handler, **kw):
    return TinyFishClient(
        cache_dir=tmp_path / "cache", call_log=tmp_path / "calls.jsonl",
        transport=httpx.MockTransport(handler), sleep=lambda s: None, **kw)


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")


def test_search_is_cached_and_logged(tmp_path):
    calls = []

    def handler(req):
        calls.append(req)
        assert req.headers["X-API-Key"] == "test-key"
        return httpx.Response(200, json={"query": "q", "results": [{"url": "u"}], "total_results": 1})

    tf = make_client(tmp_path, handler)
    assert tf.search("q")["results"][0]["url"] == "u"
    assert tf.search("q")["total_results"] == 1
    assert len(calls) == 1  # second call served from cache
    assert usage_summary(tmp_path / "calls.jsonl")["search"] == {"live": 1, "cached": 1, "errors": 0}


def test_retries_on_429_then_succeeds(tmp_path):
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(429)
        return httpx.Response(200, json={"results": [], "errors": []})

    tf = make_client(tmp_path, handler)
    assert tf.fetch(["https://example.com"])["results"] == []
    assert state["n"] == 3


def test_gives_up_after_retries(tmp_path):
    tf = make_client(tmp_path, lambda req: httpx.Response(503), max_retries=2)
    with pytest.raises(RuntimeError, match="after retries"):
        tf.search("q")


def test_client_error_not_retried(tmp_path):
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        return httpx.Response(401, text="bad key")

    tf = make_client(tmp_path, handler)
    with pytest.raises(RuntimeError, match="401"):
        tf.search("q")
    assert state["n"] == 1


def test_dry_run_requires_cache(tmp_path):
    tf = make_client(tmp_path, lambda req: httpx.Response(200, json={}), dry_run=True)
    with pytest.raises(CacheMiss):
        tf.search("never cached")


def test_fetch_batch_limit(tmp_path):
    tf = make_client(tmp_path, lambda req: httpx.Response(200, json={}))
    with pytest.raises(ValueError):
        tf.fetch([f"https://e.com/{i}" for i in range(11)])


def test_missing_key_message(tmp_path, monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY")
    tf = make_client(tmp_path, lambda req: httpx.Response(200, json={}))
    with pytest.raises(RuntimeError, match="TINYFISH_API_KEY"):
        tf.search("q")


def test_agent_cap(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "AGENT_RUN_CAP", 1)
    tf = make_client(tmp_path, lambda req: httpx.Response(200, json={"status": "COMPLETED", "result": {}}))
    tf.run_agent("https://x.org", "goal a")
    from app.tinyfish_client import AgentCapReached
    with pytest.raises(AgentCapReached):
        tf.run_agent("https://x.org", "goal b")
    json.dumps(tf.run_agent("https://x.org", "goal a"))  # cached, no cap hit
