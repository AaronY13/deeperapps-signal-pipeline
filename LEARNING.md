# Learning Log

Running notes on what I've actually learned while building this, in my own
words. One entry per session. Not a changelog of what got built — a record
of what clicked.

## 2026-08-11

- Talked through the project goal with Brandon: stop waiting for complete
  understanding before acting. Build something small, let it break, learn
  from the gap between what I built and what I expected.
- Starting point: `ingest.py` already pulls RSS + HN into `data/raw_items.json`.
- Decided my role on this project is understanding workflow, architecture,
  and concepts well enough to explain them back — not writing code by hand.
  Claude builds it, explains each function and any new concept as it goes.
- Built `dedup.py`. Checked real data first instead of guessing: 2,100 items,
  zero duplicate URLs, but found "Team Update" appearing 3x with DIFFERENT
  content (Jan vs Aug) — same generic title, not the same story. That's why
  dedup matches on URL, not title: title-matching would've wrongly merged
  those.
- New concept: a Python `set` is a fast "have I seen this?" lookup (like a
  guest list at a door) — used to track seen URLs in one pass instead of
  re-scanning the whole list each time.
- Known gap, on purpose, not solved yet: two different URLs that are
  genuinely the same content (found one real example: OpenAI's "State of
  Enterprise AI" report lives at two different site paths) won't be caught
  by URL-only matching. Revisit only if this turns out to happen often.
- Wanted a frontend to view the data instead of reading raw JSON. Key
  concept: a plain static HTML file (opened by double-click, no server)
  CANNOT reach out to live RSS/HN feeds itself — browsers block that kind
  of cross-site fetch from a bare file, and Python is doing that job
  already in ingest.py (daily, via GitHub Actions). So "live" data already
  exists, just not fetched from inside the HTML. Built `frontend/index.html`
  instead: a file-picker loads whatever JSON ingest.py/dedup.py most
  recently wrote, renders it as a sortable/filterable table. Static,
  local-only, matches current project scope.
- Wanted the table to auto-populate instead of manually picking a file each
  time. Learned why that wasn't possible before: a page opened by double-
  clicking (`file://`) is blocked by the browser from fetching sibling
  files — that's a real security boundary (CORS), not a bug. Fix: run a
  tiny local server (`python3 -m http.server` from the project root) so
  the page is served over `http://localhost:8000` instead of `file://`,
  which lifts that restriction. The frontend now calls `fetch()` on page
  load to grab `data/deduped_items.json` automatically, with a Reload
  button and a Raw/Deduped dropdown. Still not "live" in the sense of
  hitting OpenAI/HN directly — it reflects whatever's on disk, refreshed
  on demand. A real publicly-hosted live site is the bigger Phase 3+5 step
  (needs Supabase + hosting), deliberately deferred.
