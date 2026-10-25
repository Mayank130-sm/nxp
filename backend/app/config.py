"""Central configuration. Secrets come only from environment / .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "neurorx.db"
CALL_LOG = DATA_DIR / "tinyfish_calls.jsonl"
GRAPH_JSON = DATA_DIR / "graph.json"
RESULTS_DIR = ROOT / "results"

# --- TinyFish (verified against docs.tinyfish.ai) ---
TINYFISH_SEARCH_URL = "https://api.search.tinyfish.ai"
TINYFISH_FETCH_URL = "https://api.fetch.tinyfish.ai"
TINYFISH_AGENT_URL = "https://agent.tinyfish.ai/v1/automation"
TINYFISH_RUNS_URL = "https://agent.tinyfish.ai/v1/runs"
SEARCH_PER_MIN = 30  # docs: 30 req/min per key
FETCH_URLS_PER_MIN = 150  # docs: 150 URLs/min per key
FETCH_BATCH_MAX = 10  # docs: up to 10 URLs per request
AGENT_RUN_CAP = int(os.getenv("AGENT_RUN_CAP", "30"))
HTTP_TIMEOUT = float(os.getenv("TINYFISH_TIMEOUT", "150"))  # seconds; raise for slow Agent runs

# --- Ollama ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# --- NCBI ---
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

# --- Evidence grading weights (sum to 100; documented in README) ---
WEIGHTS = {
    "replication": 25,
    "design": 25,
    "markers": 20,
    "species": 20,
    "dose": 10,
}
PENALTIES = {"single_lab": 10, "contradiction": 15, "unverified_quote": 50}


def tinyfish_key() -> str:
    key = os.getenv("TINYFISH_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "TINYFISH_API_KEY is not set. Create a key at https://agent.tinyfish.ai/api-keys "
            "and put it in .env (see .env.example)."
        )
    return key
