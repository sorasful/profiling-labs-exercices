import gzip
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import requests

DELTA_BASE_URL = "http://localhost:8017"
DB_PATH = Path(__file__).parent / "products.db"

def open_db() -> sqlite3.Connection:
    DB_PATH.unlink(missing_ok=True)  # drop the DB: every run re-imports everything
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE products (
            code TEXT PRIMARY KEY,
            name TEXT,
            brands TEXT,
            countries TEXT,
            last_modified INTEGER
        )
        """
    )
    return conn


def delta_filenames() -> list[str]:
    response = requests.get(f"{DELTA_BASE_URL}/index.txt", timeout=30)
    response.raise_for_status()
    return [l.strip() for l in response.text.splitlines() if l.strip()]

def parse_product(record: dict) -> tuple | None:
    code = record.get("code") or record.get("_id")
    if not code:
        return None
    return (
        code,
        record.get("product_name") or None,
        record.get("brands") or None,
        record.get("countries") or None,
        record.get("last_modified_t"),
    )

def checksum(conn: sqlite3.Connection) -> str:
    h = hashlib.sha256()
    for row in conn.execute(
        "SELECT code, name, brands, countries, last_modified FROM products ORDER BY code"
    ):
        h.update(repr(row).encode())
    return h.hexdigest()[:16]


def cmd_run() -> int:
    conn = open_db()
    filenames = delta_filenames()

    scanned = 0
    for filename in filenames:
        response = requests.get(f"{DELTA_BASE_URL}/{filename}", timeout=120)
        response.raise_for_status()
        raw = gzip.decompress(response.content)
        for line in raw.splitlines():
            if not line:
                continue
            product = parse_product(json.loads(line))
            if product is None:
                continue
            scanned += 1
            conn.execute("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?)", product)
        print(f"  {filename} done")
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"{len(filenames)} files, {scanned} scanned, {total} products, checksum={checksum(conn)}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(cmd_run())
