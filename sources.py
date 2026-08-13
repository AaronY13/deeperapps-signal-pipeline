"""
Tier 0 source list — free, no API key required.

Status notes (checked 2026-08-12):
  - openai, deepmind, huggingface, google: official feeds, returned HTTP 200 / valid XML.
  - anthropic: Anthropic does not publish an official RSS feed. Using a
    community-maintained mirror (tim-hilde/anthropic-rss). Unofficial — expect
    this one to be the most likely to break. Revisit if it goes stale.
  - mistral, meta, microsoft: no working RSS feed (404/410 on the URLs we could
    find). Left out. Check back later or watch their sites directly.
  - nvidia, MIT Technology Review: feeds work, but cover far more than AI
    (gaming, general tech) — same noise problem HN's top-stories had. Left
    out until there's a relevance filter worth applying to them too.
  - arXiv cs.AI: feed works and is on-topic, but is a different kind of
    source (academic papers, 750+ items/pull) — a separate "research" bucket,
    not "industry news." Deliberately left out of this pass.

Add sources here as you evaluate them. If a feed 404s or times out
repeatedly, cut it — a dead source that gets silently skipped every run is
worse than no source, because it looks like coverage you don't actually have.
"""

RSS_FEEDS = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/feed/basic/"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Anthropic (unofficial mirror)", "url": "https://tim-hilde.github.io/anthropic-rss/rss.xml"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
]

# Hacker News: Algolia's public search API (no key, no rate limit), searched
# by AI-related keywords and sorted by date. Deliberately NOT the plain
# "top stories" endpoint — checked real output and found top-stories is
# mostly unrelated to AI (cocktail recipes, math history, etc). A keyword
# search is a blunt filter, not real relevance judgment (that's Phase 4's
# job), but it's a large, confirmed improvement over unfiltered trending.
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_SEARCH_QUERY = "AI"
HN_MIN_POINTS = 20  # cuts low-signal/likely-dead posts, keeps real discussion
HN_ITEM_LIMIT = 30  # cap per run — keep this barebones script cheap and fast

RECENCY_DAYS = 30  # drop anything older than this at ingest time
