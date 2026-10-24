"""P0 smoke test: structured JSON from local Ollama."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.llm import OllamaLLM

schema = {
    "type": "object",
    "properties": {"drug": {"type": ["string", "null"]}, "direction": {"enum": ["increase", "decrease", "no_effect", "mixed", None]}},
    "required": ["drug", "direction"],
}
llm = OllamaLLM()
print(f"model: {llm.model}")
out = llm.complete_json(
    "Extract facts. If the text does not state it, return null. Do not infer.",
    "Fluoxetine treatment increased the number of BrdU+ cells in the dentate gyrus of mice.",
    schema,
)
print(out)
