import argparse
import json
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path

import requests
from rich.console import Console
from rich.table import Table

DELTA_BASE_URL = "https://static.openfoodfacts.org/data/delta"
DB_PATH = Path(__file__).parent / "products.db"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"}

console = Console()


def cmd_ping() -> int:
    # Timeout flag differs: -W on Linux, -t on macOS/BSD
    timeout_flag = "-W" if sys.platform.startswith("linux") else "-t"
    result = subprocess.run(
        ["ping", "-c", "1", timeout_flag, "3", "1.1.1.1"],
        capture_output=True,
    )
    if result.returncode == 0:
        print('OK')
        return 0
    print('NOT OK')
    return 1


def open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            code TEXT PRIMARY KEY,
            name TEXT,
            brands TEXT,
            countries TEXT,
            last_modified INTEGER
        )
        """
    )
    return conn


def latest_delta_filename() -> str:
    response = requests.get(f"{DELTA_BASE_URL}/index.txt", headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text.splitlines()[0].strip()


def iter_delta_products(filename: str):
    """Download the gzipped JSONL delta file and yield one product dict per
    line, decompressing on the fly."""
    decompressor = zlib.decompressobj(wbits=47)  # 47 = gzip auto-detection
    buffer = b""
    with requests.get(
        f"{DELTA_BASE_URL}/{filename}", headers=HEADERS, stream=True, timeout=60
    ) as response:
        response.raise_for_status()
        for chunk in response.iter_content(256 * 1024):
            buffer += decompressor.decompress(chunk)
            *lines, buffer = buffer.split(b"\n")
            for line in lines:
                if line:
                    yield json.loads(line)
    remainder = decompressor.flush() + buffer
    if remainder.strip():
        yield json.loads(remainder)


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


def cmd_run() -> int:
    conn = open_db()
    new_products = []
    scanned = 0

    try:
        filename = latest_delta_filename()
        with console.status(f"Downloading {filename}…"):
            for record in iter_delta_products(filename):
                product = parse_product(record)
                if product is None:
                    continue
                scanned += 1
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?)", product
                )
                if cursor.rowcount:  # 0 if the code already existed (duplicate)
                    new_products.append(product)
    except requests.RequestException as exc:
        console.print(f"[bold red]Network error:[/bold red] {exc}")
        return 1
    finally:
        conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()

    if new_products:
        table = Table(title=f"{len(new_products)} new products")
        table.add_column("Code", style="dim")
        table.add_column("Name", style="cyan", max_width=45)
        table.add_column("Brands", max_width=25)
        table.add_column("Countries", max_width=25)
        for code, name, brands, countries, _ in new_products:
            table.add_row(code, name or "(no name)", brands or "?", countries or "?")
        console.print(table)
    else:
        console.print("[yellow]No new products (duplicates only).[/yellow]")

    console.print(
        f"{scanned} products scanned, [green]{len(new_products)} added[/green], "
        f"{total} total in [bold]{DB_PATH.name}[/bold]"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ping", help="Ping 1.1.1.1 and print OK")
    sub.add_parser("run", help="Import the latest Open Food Facts delta into SQLite")

    args = parser.parse_args()
    if args.command == "ping":
        return cmd_ping()
    return cmd_run()


if __name__ == "__main__":
    sys.exit(main())
