"""
Dedup pass over raw_items.json. Matches on exact URL only — deliberately
conservative. Title-matching was tried and rejected: real data showed
generic recurring titles ("Team Update") that are NOT the same story,
just the same headline reused across different posts. Matching on URL
avoids that false-positive trap.

Known gap: two items with different URLs but genuinely the same content
(e.g. a report published under two different site paths) won't be caught.
Revisit if that turns out to happen often — not solving it speculatively.

Run: .venv/bin/python3 dedup.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def dedup_by_url(items: list[dict]) -> list[dict]:
    """Keep the first occurrence of each URL, drop the rest."""
    seen_urls = set()
    deduped = []
    for item in items:
        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)
    return deduped


def main():
    raw_path = DATA_DIR / "raw_items.json"
    items = json.loads(raw_path.read_text())

    deduped = dedup_by_url(items)
    removed = len(items) - len(deduped)

    out_path = DATA_DIR / "deduped_items.json"
    out_path.write_text(json.dumps(deduped, indent=2))

    print(f"Input:  {len(items)} items")
    print(f"Output: {len(deduped)} items ({removed} duplicates removed)")
    print(f"Written to: {out_path}")


if __name__ == "__main__":
    main()
