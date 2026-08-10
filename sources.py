"""
Tier 0 source list — free, no API key required.

Status notes (checked 2026-08-09):
  - openai, deepmind, huggingface: official feeds, returned HTTP 200 / valid XML.
  - anthropic: Anthropic does not publish an official RSS feed. Using a
    community-maintained mirror (tim-hilde/anthropic-rss). Unofficial — expect
    this one to be the most likely to break. Revisit if it goes stale.
  - mistral: no RSS feed found (official or otherwise). Left out for now;
    check back later or watch their site directly.

Add sources here as you evaluate them. If a feed 404s or times out
repeatedly, cut it — a dead source that gets silently skipped every run is
worse than no source, because it looks like coverage you don't actually have.
"""

RSS_FEEDS = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/feed/basic/"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Anthropic (unofficial mirror)", "url": "https://tim-hilde.github.io/anthropic-rss/rss.xml"},
]

# Hacker News: Firebase API for the live feed, no key, no rate limit.
# https://github.com/HackerNews/API
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_ITEM_LIMIT = 30  # cap per run — keep this barebones script cheap and fast
