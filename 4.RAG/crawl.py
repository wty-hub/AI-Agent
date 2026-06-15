import json
import time
from pathlib import Path

import requests

from wikisource_clean import clean_wikitext, extract_header_meta

API = "https://zh.wikisource.org/w/api.php"
HEADERS = {"User-Agent": "QingHistoryBot/1.0 (research; contact@example.com)"}
OUTPUT = Path("wikisource_data")


def api_get(params: dict) -> dict:
    r = requests.get(API, params={**params, "format": "json"}, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def list_all_pages(prefix: str) -> list[str]:
    titles, params = [], {
        "action": "query",
        "list": "allpages",
        "apprefix": prefix,
        "aplimit": "max",
    }
    while True:
        data = api_get(params)
        titles.extend(p["title"] for p in data["query"]["allpages"])
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(0.3)
    return titles


def fetch_page(title: str) -> dict:
    data = api_get(
        {
            "action": "query",
            "titles": title,
            "prop": "revisions|info",
            "rvprop": "content|timestamp",
            "rvslots": "main",
            "inprop": "url",
        }
    )
    page = next(iter(data["query"]["pages"].values()))
    return {
        "title": page["title"],
        "url": page["fullurl"],
        "timestamp": page["revisions"][0]["timestamp"],
        "content": page["revisions"][0]["slots"]["main"]["*"],
    }


SKIP_TITLES = {"清史稿", "清實錄"}


def crawl(prefix: str, out_dir: Path, limit: int | None = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = list_all_pages(prefix)
    print(f"Found {len(pages)} pages under {prefix}")

    fetched = 0
    for i, title in enumerate(pages, 1):
        if title in SKIP_TITLES:
            continue
        safe_name = title.replace("/", "__")
        out_file = out_dir / f"{safe_name}.json"
        if out_file.exists():
            continue
        if limit is not None and fetched >= limit:
            break

        try:
            page = fetch_page(title)
            meta = extract_header_meta(page["content"])
            page["section"] = meta.get("section", "")
            page["author"] = meta.get("author", "")
            page["plain_text"] = clean_wikitext(page["content"])
            out_file.write_text(
                json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            fetched += 1
        except Exception as e:
            print(f"Error on {title}: {e}")

        if i % 10 == 0:
            print(f"  {i}/{len(pages)} done")
        time.sleep(0.5)


if __name__ == "__main__":
    crawl("清史稿", OUTPUT / "清史稿")
    crawl("清實錄", OUTPUT / "清實錄")
