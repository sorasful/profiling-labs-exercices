import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

DATA_URL = (
    "https://raw.githubusercontent.com/sorasful/profiling-labs-exercices"
    "/main/1_3_pyinstrument_profiling/assets/data.json"
)
IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:129.0) Gecko/20100101 Firefox/129.0"}

IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"')


def fetch_document(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return json.loads(response.text)


def download_image(url: str, target_dir: Path = IMAGES_DIR) -> bool:
    filename = unquote(Path(urlparse(url).path).name)
    print(f"Downloading image {filename}")
    target = target_dir / filename
    response = requests.get(url, headers=HEADERS, timeout=60)
    if response.status_code != 200:
        print(f"    skipped {filename} (HTTP {response.status_code})")
        return False
    target.write_bytes(response.content)
    return True


def main() -> int:
    print(f"Fetching document {DATA_URL.rsplit('/', 1)[-1]} ...")
    document = fetch_document(DATA_URL)
    title = document["title"]
    content = document["content"]
    print(f"[{title}] ({document['date']}), parsing…")

    image_urls = IMG_SRC_RE.findall(content)
    print(f"[{title}] found {len(image_urls)} image links, downloading…")

    downloaded = 0
    for i, image_url in enumerate(image_urls, 1):
        if download_image(image_url):
            downloaded += 1

    print(f"Done: {downloaded} images saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
