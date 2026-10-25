"""Thin typed wrapper over TinyFish Search, Fetch and Agent APIs.

Features: on-disk cache, token-bucket rate limiting, retries with backoff,
dry-run (cache only) mode, and a JSONL call log for real usage numbers.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from . import config


class CacheMiss(RuntimeError):
    """Raised in dry-run mode when a request is not cached."""


class AgentCapReached(RuntimeError):
    """Raised when the configured Agent run cap is hit."""


class TokenBucket:
    """Allows `rate` tokens per minute; blocks until enough tokens are available."""

    def __init__(self, rate_per_min: float) -> None:
        self.capacity = rate_per_min
        self.tokens = rate_per_min
        self.rate = rate_per_min / 60.0
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def take(self, n: float = 1.0) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                wait = (n - self.tokens) / self.rate
            time.sleep(wait)


class TinyFishClient:
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Path | None = None,
        call_log: Path | None = None,
        max_retries: int = 4,
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self.dry_run = dry_run
        self.cache_dir = cache_dir or config.CACHE_DIR / "tinyfish"
        self.call_log = call_log or config.CALL_LOG
        self.max_retries = max_retries
        self._sleep = sleep
        self._http = httpx.Client(transport=transport, timeout=httpx.Timeout(config.HTTP_TIMEOUT, connect=15.0))
        self._search_bucket = TokenBucket(config.SEARCH_PER_MIN)
        self._fetch_bucket = TokenBucket(config.FETCH_URLS_PER_MIN)
        self.agent_runs = 0

    # ---- public API ----
    def search(self, query: str, **params: Any) -> dict[str, Any]:
        """GET Search API. Returns {query, results[], total_results, page}."""
        p = {"query": query, "location": "US", "language": "en", **params}
        return self._cached("search", p, lambda: self._request(
            "search", "GET", config.TINYFISH_SEARCH_URL, params=p, bucket=self._search_bucket))

    def fetch(self, urls: list[str], fmt: str = "markdown", **extra: Any) -> dict[str, Any]:
        """POST Fetch API (<=10 URLs). Returns {results[], errors[]}."""
        if len(urls) > config.FETCH_BATCH_MAX:
            raise ValueError(f"Fetch accepts at most {config.FETCH_BATCH_MAX} URLs per call")
        body = {"urls": urls, "format": fmt, **extra}
        return self._cached("fetch", body, lambda: self._request(
            "fetch", "POST", config.TINYFISH_FETCH_URL, json_body=body,
            bucket=self._fetch_bucket, cost=len(urls)))

    def run_agent(
        self, url: str, goal: str, output_schema: dict | None = None, stream: bool = False
    ) -> dict[str, Any]:
        """Run a TinyFish Agent goal. Sync endpoint by default, SSE if stream=True.

        Returns the final run object: {run_id, status, result, error, ...}.
        """
        body: dict[str, Any] = {"url": url, "goal": goal}
        if output_schema:
            body["output_schema"] = output_schema
        key_params = {**body, "stream": stream}

        def call() -> dict[str, Any]:
            if self.agent_runs >= config.AGENT_RUN_CAP:
                raise AgentCapReached(f"Agent run cap {config.AGENT_RUN_CAP} reached")
            self.agent_runs += 1
            if stream:
                return self._agent_sse(body)
            return self._request("agent", "POST", f"{config.TINYFISH_AGENT_URL}/run", json_body=body)

        return self._cached("agent", key_params, call)

    # ---- internals ----
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": config.tinyfish_key()}

    def _cache_path(self, endpoint: str, params: dict) -> Path:
        digest = hashlib.sha256(
            json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()[:32]
        return self.cache_dir / endpoint / f"{digest}.json"

    def _cached(self, endpoint: str, params: dict, call: Any) -> dict[str, Any]:
        path = self._cache_path(endpoint, params)
        if path.exists():
            self._log(endpoint, 0.0, True, 200, params)
            return json.loads(path.read_text(encoding="utf-8"))
        if self.dry_run:
            raise CacheMiss(f"dry-run: no cached response for {endpoint} {params}")
        data = call()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def _request(
        self, endpoint: str, method: str, url: str, params: dict | None = None,
        json_body: dict | None = None, bucket: TokenBucket | None = None, cost: float = 1.0,
    ) -> dict[str, Any]:
        last_err = ""
        for attempt in range(self.max_retries + 1):
            if bucket:
                bucket.take(cost)
            start = time.monotonic()
            try:
                resp = self._http.request(
                    method, url, params=params, json=json_body, headers=self._headers())
            except httpx.TransportError as exc:
                last_err = f"transport error: {exc.__class__.__name__}"
                self._log(endpoint, time.monotonic() - start, False, 0, params or json_body)
                self._sleep(min(2 ** attempt, 30))
                continue
            latency = time.monotonic() - start
            self._log(endpoint, latency, False, resp.status_code, params or json_body)
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = f"HTTP {resp.status_code}"
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
                self._sleep(min(delay, 60))
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"TinyFish {endpoint} failed: HTTP {resp.status_code} {resp.text[:300]}")
            return resp.json()
        raise RuntimeError(f"TinyFish {endpoint} failed after retries ({last_err})")

    def _agent_sse(self, body: dict) -> dict[str, Any]:
        """Consume run-sse and return the COMPLETE event payload."""
        start = time.monotonic()
        final: dict[str, Any] = {}
        with self._http.stream(
            "POST", f"{config.TINYFISH_AGENT_URL}/run-sse", json=body, headers=self._headers()
        ) as resp:
            if resp.status_code >= 400:
                raise RuntimeError(f"TinyFish agent SSE failed: HTTP {resp.status_code}")
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "COMPLETE":
                    final = event
        self._log("agent", time.monotonic() - start, False, 200, body)
        return final

    def _log(self, endpoint: str, latency: float, cache_hit: bool, status: int, params: Any) -> None:
        self.call_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "endpoint": endpoint,
            "latency_s": round(latency, 3),
            "cache_hit": cache_hit,
            "status": status,
            "params_digest": hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:12],
        }
        with self.call_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


def usage_summary(call_log: Path | None = None) -> dict[str, dict[str, int]]:
    """Summarise the call log: live calls vs cache hits per endpoint."""
    path = call_log or config.CALL_LOG
    out: dict[str, dict[str, int]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        row = out.setdefault(e["endpoint"], {"live": 0, "cached": 0, "errors": 0})
        if e["cache_hit"]:
            row["cached"] += 1
        elif 200 <= e["status"] < 300:
            row["live"] += 1
        else:
            row["errors"] += 1
    return out
