"""Screenshot every screen at desktop and mobile widths and flag horizontal overflow.

Serves the built static frontend (run `npm run build` after `scripts/export_static.py`), then drives Chromium.
Usage: screenshots.py [--drug fluoxetine]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "screens"
SIZES = {"desktop": (1440, 900), "mobile": (390, 844)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drug", default="fluoxetine")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    server = subprocess.Popen([npx, "vite", "preview", "--port", "4173", "--strictPort"], cwd=ROOT / "frontend",
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    pages = {"1-ranking": "/", "2-drug": f"/drug/{args.drug}", "3-graph": "/graph", "4-methods": "/methods"}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for label, (w, h) in SIZES.items():
                page = browser.new_page(viewport={"width": w, "height": h})
                errors: list[str] = []
                page.on("pageerror", lambda e, sink=errors: sink.append(str(e)))
                for name, route in pages.items():
                    page.goto(f"http://localhost:4173/#{route}")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2500 if "graph" in name else 1200)
                    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    page.screenshot(path=str(OUT / f"{name}-{label}.png"), full_page="graph" not in name)
                    if label == "mobile":
                        page.screenshot(path=str(OUT / f"{name}-{label}-fold.png"), full_page=False)
                    print(f"{name:12s} {label:8s} overflow={overflow}px")
                if errors:
                    print("page errors:", errors)
            browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
