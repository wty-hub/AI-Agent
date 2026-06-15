import json
from pathlib import Path

from wikisource_clean import clean_wikitext, extract_header_meta

DATA_DIR = Path("wikisource_data")


def clean_corpus(data_dir: Path = DATA_DIR) -> None:
    for book_dir in sorted(data_dir.iterdir()):
        if not book_dir.is_dir():
            continue
        count = 0
        for path in sorted(book_dir.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            meta = extract_header_meta(doc.get("content", ""))
            doc["section"] = meta.get("section", "")
            doc["author"] = meta.get("author", "")
            doc["plain_text"] = clean_wikitext(doc.get("content", ""))
            path.write_text(
                json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            count += 1
        print(f"{book_dir.name}: cleaned {count} files")


if __name__ == "__main__":
    clean_corpus()
