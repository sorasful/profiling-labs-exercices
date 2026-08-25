import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

REAL_BASE = "https://static.openfoodfacts.org/data/delta"
CACHE = Path(__file__).parent / "delta_cache"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"}
PORT = 8017


def get(url: str) -> requests.Response:
    for attempt in range(6):
        response = requests.get(url, headers=HEADERS, timeout=120)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        wait = 30 * (attempt + 1)
        print(f"  429 rate-limited, waiting {wait}s...")
        time.sleep(wait)
    response.raise_for_status()
    return response


def fetch() -> None:
    CACHE.mkdir(exist_ok=True)
    index_file = CACHE / "index.txt"
    if not index_file.exists():
        index_file.write_bytes(get(f"{REAL_BASE}/index.txt").content)
    filenames = [l.strip() for l in index_file.read_text().splitlines() if l.strip()]
    for i, filename in enumerate(filenames, 1):
        target = CACHE / filename
        if target.exists() and target.stat().st_size > 0:
            print(f"  [{i}/{len(filenames)}] {filename} (cached)")
            continue
        print(f"  [{i}/{len(filenames)}] {filename} downloading...")
        target.write_bytes(get(f"{REAL_BASE}/{filename}").content)
        time.sleep(2)  # be nice to OFF
    print(f"cache ready: {len(filenames)} files in {CACHE}")


def serve() -> None:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(CACHE), **kwargs)

        def log_message(self, *args):
            pass

    print(f"serving {CACHE} on http://localhost:{PORT}")
    print("keep this running, then launch main.py in another terminal")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    fetch()
    sys.exit(serve())
