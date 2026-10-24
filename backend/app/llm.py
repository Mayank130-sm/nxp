"""LLM interface. Ollama is the default backend; swap by implementing LLM."""
from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from . import config


class LLM(Protocol):
    model: str

    def complete_json(self, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object conforming to `schema` (temperature 0)."""
        ...


class OllamaLLM:
    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or config.OLLAMA_MODEL
        self.host = (host or config.OLLAMA_HOST).rstrip("/")
        self._http = httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0))

    def complete_json(self, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        resp = self._http.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "think": False,  # skip reasoning tokens; the schema constrains the answer
                "format": schema,  # structured outputs: constrain to JSON schema
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        return json.loads(resp.json()["message"]["content"])
