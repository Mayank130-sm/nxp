"""One-command dev start (Windows, macOS, Linux): FastAPI on :8000 and the Vite UI on :5173.

Usage: python scripts/dev.py   (Ctrl-C stops both). The UI is wired to the API through VITE_API_URL.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PORT, WEB_PORT = 8000, 5173


def wait_for(url: str, name: str, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"[dev] {name} ready: {url}")
            return
        except OSError:
            time.sleep(1)
    sys.exit(f"[dev] {name} did not start within {timeout:.0f}s")


def main() -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--port", str(API_PORT)], cwd=ROOT)
    env = {**os.environ, "VITE_API_URL": f"http://localhost:{API_PORT}"}
    web = subprocess.Popen([npm, "run", "dev", "--", "--port", str(WEB_PORT), "--strictPort"], cwd=ROOT / "frontend", env=env)
    procs = [api, web]
    try:
        wait_for(f"http://localhost:{API_PORT}/health", "API")
        wait_for(f"http://localhost:{WEB_PORT}/", "UI")
        print(f"[dev] open http://localhost:{WEB_PORT}  (Ctrl-C to stop)")
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
