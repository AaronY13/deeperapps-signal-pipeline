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

## 2026-08-12

- Checked run history instead of assuming: local `ingest.py` had only run
  once (one manual run), but the GitHub Actions schedule had already fired
  automatically twice in the cloud. Lesson: local files and cloud runs are
  two separate copies that don't sync with each other unless you build
  something that connects them.
- Deployed the frontend as a real public website using **GitHub Pages**.
  Had to make the repo public first (Pages needs a public repo on the free
  plan). Also had to stop `.gitignore`-ing `data/*.json` and change the
  daily workflow to commit each day's data into the repo — otherwise the
  deployed static site would have nothing to display. Side benefit: git's
  commit history now doubles as a crude "history log" of past days' data,
  even without a real database yet.
- **GitHub, in plain terms:** a cloud storage locker for a project's files
  that also remembers every past saved version (commit history).
- **GitHub Actions vs. GitHub Pages — the core distinction:**
  - Actions = a robot that *does work*. It only wakes up for a trigger
    (schedule, manual button, a push, or an authenticated API call) and
    runs real code on a temporary computer ("runner").
  - Pages = *pure static hosting*. No code runs when someone visits — it's
    a file-handout window, nothing more. Reloading the page never re-runs
    anything; it just re-displays whatever files are currently committed.
- **Why the site can't fetch fresh articles on every reload** (asked
  directly, real architecture reasons, not a missing setting):
  - GitHub Pages has zero compute — nothing executes per visit, so there's
    nothing on the Pages side capable of "calling" ingest.py in the first
    place.
  - The only bridge to Actions is GitHub's API, which requires a secret
    access token to authorize. Putting that secret inside public webpage
    code would let any visitor steal it (view source / dev tools) and gain
    control of the repo — a real security hole, not just an inconvenience.
  - Even ignoring security, triggering a full fetch (external RSS/HN calls
    + git commit) on every single page visit doesn't scale and isn't
    actually "instant" anyway — ingest.py takes real time to run.
  - Freshness is instead controlled by the cron schedule in
    `daily-ingest.yml` (currently once/day) — a dial that can be turned
    (e.g. hourly) but can't reach true per-reload freshness without
    swapping Pages for a different kind of hosting entirely.
- **CDN concept:** a Content Delivery Network is just many copies of the
  same files parked on servers around the world, so whoever loads the
  site gets served from a nearby copy instead of one far-away origin.
  Both GitHub Pages and AWS CloudFront work this way for static files.
- **GitHub Pages vs. AWS CloudFront:** similar at the base layer (both
  hand out static files fast via a CDN), but CloudFront is a raw building
  block AWS lets you attach real per-request compute to (Lambda@Edge /
  CloudFront Functions — actual code that runs on every visit). GitHub
  Pages has no equivalent attachment point. "Live on every reload" is a
  real, common pattern — it's just built with tools like CloudFront+Lambda
  or Vercel/Netlify functions, not GitHub Pages.
- Decided live compute wasn't the priority yet — went back to the actual
  data pipeline instead: sources, collection, and cleaning. Checked real
  data before planning (not assumptions): Hacker News "top stories" turned
  out to be ~90% NOT AI-related (cocktail recipes, math history, a weather
  app complaint), and OpenAI's RSS feed alone went back to 2018 with no
  recency filter — a "daily news" tool showing a 2018 post as current is
  broken, not just untidy.
- Fixed HN relevance: swapped the "top stories" endpoint for HN's free
  Algolia Search API (`search_by_date`), searched by keyword ("AI") with a
  minimum points threshold, instead of pulling whatever's trending
  regardless of topic. Result: went from ~3-4 relevant items out of 30 to
  ~27-28 out of 30. Still a blunt keyword filter, not real judgment — a
  couple of false positives got through (an article about air traffic
  controllers that happened to mention "AI"). Real relevance judgment is
  Phase 4's job, not this fix's.
- Added a 30-day recency filter (`filter_recent` in ingest.py). Confirmed
  it works on real data: 2,133 items pulled, 1,995 dropped as >30 days old,
  138 kept. Learned `feedparser` already provides a reliably-parsed date
  (`entry.published_parsed`) that wasn't being used before — was only
  storing a raw, inconsistently-formatted string. Normalized every source
  (RSS and HN) to the same ISO 8601 date format so filtering/sorting works
  the same way everywhere instead of guessing per-source formats.
- Added `summary` field, pulled from RSS entries when the source provides
  one. Checked first instead of assuming: OpenAI's feed includes a clean
  summary, Hugging Face's doesn't — so it's populated when available, left
  blank otherwise. No fabricated content.
- Added one new source, Google AI Blog — but only after testing candidates
  live first. Tried Meta AI, Microsoft AI, and Mistral blogs: all dead
  (404/410). Tried NVIDIA and MIT Technology Review: both work, but cover
  far more than AI (same noise problem HN just had) — left out rather than
  building a second relevance filter for them in the same round. Tried
  arXiv cs.AI: works and is on-topic, but is a different kind of source
  (academic papers, 750+ items per pull) — deliberately scoped out as
  "research," not "industry news."
- Re-ran `dedup.py` against the cleaner, larger dataset — still 0 exact-URL
  duplicates, logic unchanged. Noted a real limit: cross-source duplicates
  (e.g. Google's blog and OpenAI's blog covering the same announcement)
  never share a URL, so URL-based dedup can't catch them — that's a "is
  this actually the same story" problem, which needs real judgment
  (Phase 4/LLM scoring), not a heuristic bolted on now.
