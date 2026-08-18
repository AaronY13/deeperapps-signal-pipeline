"""
Barebones ingestion: pull raw items from Tier 0 sources and dump them to
data/raw_items.json. No dedup, no scoring, no storage beyond a flat file.
The only job right now is: prove we can reliably pull items and see what
they actually look like.

Run: .venv/bin/python3 ingest.py
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx
from dotenv import load_dotenv
from supabase import create_client

from sources import (
    RSS_FEEDS,
    HN_SEARCH_URL,
    HN_SEARCH_QUERY,
    HN_MIN_POINTS,
    HN_ITEM_LIMIT,
    RECENCY_DAYS,
)

HEADERS = {"User-Agent": "deeperapps-signal-pipeline/0.1 (learning project)"}
TIMEOUT = 15
HTML_TAG = re.compile(r"<[^>]+>")

load_dotenv(Path(__file__).parent / ".env")


def parsed_time_to_iso(struct_time) -> str:
    """Convert feedparser's parsed date (a time.struct_time in UTC) to ISO 8601."""
    return datetime(*struct_time[:6], tzinfo=timezone.utc).isoformat()


def strip_html(text: str) -> str:
    return HTML_TAG.sub("", text).strip()


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
        struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
        published = parsed_time_to_iso(struct_time) if struct_time else ""
        items.append({
            "source": name,
            "source_type": "rss",
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "published": published,
            "summary": strip_html(entry.get("summary", "")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    print(f"  [OK]   {name}: {len(items)} items")
    return items


def fetch_hn_ai_stories(limit: int = HN_ITEM_LIMIT) -> list[dict]:
    """
    Fetch AI-related Hacker News stories via Algolia's search API, sorted by
    date. Deliberately not "top stories" — that endpoint returns whatever's
    trending regardless of topic (checked real output: mostly not AI news).
    A keyword search + minimum points is a blunt filter, not real relevance
    judgment, but a confirmed improvement over unfiltered trending.
    """
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)).timestamp())
    params = {
        "query": HN_SEARCH_QUERY,
        "tags": "story",
        "numericFilters": f"created_at_i>{cutoff},points>{HN_MIN_POINTS}",
        "hitsPerPage": limit,
    }
    try:
        resp = httpx.get(HN_SEARCH_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except httpx.HTTPError as e:
        print(f"  [FAIL] Hacker News (search): {e}")
        return []

    items = []
    for hit in hits:
        story_id = hit.get("objectID")
        items.append({
            "source": "Hacker News",
            "source_type": "hn",
            "title": (hit.get("title") or "").strip(),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "published": hit.get("created_at", ""),
            "summary": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "hn_score": hit.get("points", 0),
            "hn_comments": hit.get("num_comments", 0),
        })

    print(f"  [OK]   Hacker News: {len(items)} items")
    return items


def filter_recent(items: list[dict], days: int = RECENCY_DAYS) -> list[dict]:
    """
    Drop items older than `days`. This is a "daily signal" tool, not an
    archive browser — some RSS feeds (OpenAI's, confirmed) return years of
    history on every pull, which would otherwise show up looking like news.
    Items with no parseable date are kept, not silently dropped, and counted
    separately so a parsing problem is visible instead of hidden.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept, undated, dropped = [], 0, 0
    for item in items:
        published = item.get("published", "")
        if not published:
            undated += 1
            kept.append(item)
            continue
        try:
            when = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            undated += 1
            kept.append(item)
            continue
        if when >= cutoff:
            kept.append(item)
        else:
            dropped += 1

    print(f"  Recency filter: kept {len(kept)}, dropped {dropped} (>{days}d old), {undated} undated (kept)")
    return kept


def push_to_supabase(items: list[dict]) -> None:
    """
    Upsert items into Supabase's `items` table, keyed on the `url` unique
    constraint: a new url inserts a new row, a url seen before updates that
    same row instead (refreshes fields like hn_score as a story ages).
    Never raises — this runs alongside the JSON file write, not instead of
    it, so a Supabase problem should never break the existing pipeline.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  [SKIP] Supabase: no credentials found (.env missing SUPABASE_URL/SUPABASE_SERVICE_KEY)")
        return

    try:
        client = create_client(url, key)
        client.table("items").upsert(items, on_conflict="url").execute()
        print(f"  [OK]   Supabase: upserted {len(items)} items")
    except Exception as e:
        print(f"  [FAIL] Supabase: {e}")


def main():
    all_items = []

    print(f"Fetching {len(RSS_FEEDS)} RSS feeds...")
    for feed in RSS_FEEDS:
        all_items.extend(fetch_rss_feed(feed["name"], feed["url"]))

    print("Fetching Hacker News (AI-related, by search)...")
    all_items.extend(fetch_hn_ai_stories())

    print(f"Total before recency filter: {len(all_items)}")
    all_items = filter_recent(all_items)

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "raw_items.json"
    out_path.write_text(json.dumps(all_items, indent=2))

    print("Writing to Supabase...")
    push_to_supabase(all_items)

    print(f"\nTotal items: {len(all_items)}")
    print(f"Written to: {out_path}")


if __name__ == "__main__":
    main()
