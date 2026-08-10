"""
Barebones ingestion: pull raw items from Tier 0 sources and dump them to
data/raw_items.json. No dedup, no scoring, no storage beyond a flat file.
The only job right now is: prove we can reliably pull items and see what
they actually look like.

Run: .venv/bin/python3 ingest.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx

from sources import RSS_FEEDS, HN_TOP_STORIES_URL, HN_ITEM_URL, HN_ITEM_LIMIT

HEADERS = {"User-Agent": "deeperapps-signal-pipeline/0.1 (learning project)"}
TIMEOUT = 15


def fetch_rss_feed(name: str, url: str) -> list[dict]:
    """Fetch and parse one RSS/Atom feed. Never raises — logs and returns []."""
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [FAIL] {name}: {e}")
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo:
        print(f"  [WARN] {name}: feed parsed with issues ({parsed.bozo_exception})")

    items = []
    for entry in parsed.entries:
        items.append({
            "source": name,
            "source_type": "rss",
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "published": entry.get("published", entry.get("updated", "")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    print(f"  [OK]   {name}: {len(items)} items")
    return items


def fetch_hn_top_stories(limit: int = HN_ITEM_LIMIT) -> list[dict]:
    """Fetch the top N Hacker News stories via the Firebase API."""
    try:
        resp = httpx.get(HN_TOP_STORIES_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        story_ids = resp.json()[:limit]
    except httpx.HTTPError as e:
        print(f"  [FAIL] Hacker News (story list): {e}")
        return []

    items = []
    for story_id in story_ids:
        try:
            resp = httpx.get(HN_ITEM_URL.format(id=story_id), timeout=TIMEOUT)
            resp.raise_for_status()
            item = resp.json()
        except httpx.HTTPError as e:
            print(f"  [FAIL] Hacker News item {story_id}: {e}")
            continue

        if not item or item.get("type") != "story":
            continue

        items.append({
            "source": "Hacker News",
            "source_type": "hn",
            "title": item.get("title", "").strip(),
            "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
            "published": datetime.fromtimestamp(
                item.get("time", 0), tz=timezone.utc
            ).isoformat() if item.get("time") else "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "hn_score": item.get("score", 0),
            "hn_comments": item.get("descendants", 0),
        })

    print(f"  [OK]   Hacker News: {len(items)} items")
    return items


def main():
    all_items = []

    print(f"Fetching {len(RSS_FEEDS)} RSS feeds...")
    for feed in RSS_FEEDS:
        all_items.extend(fetch_rss_feed(feed["name"], feed["url"]))

    print("Fetching Hacker News top stories...")
    all_items.extend(fetch_hn_top_stories())

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "raw_items.json"
    out_path.write_text(json.dumps(all_items, indent=2))

    print(f"\nTotal items: {len(all_items)}")
    print(f"Written to: {out_path}")


if __name__ == "__main__":
    main()
