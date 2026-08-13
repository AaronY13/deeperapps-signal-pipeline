# Signal Pipeline Anatomy

A from-scratch, file-by-file breakdown of this project — written for future-me
coming back cold. Reviewed and accurate as of 2026-08-13.

Repo: github.com/AaronY13/deeperapps-signal-pipeline (public)

---

## 1. What's actually built so far

Status: **Collect → Clean → (not started) Score → (not started) Deliver**

The end goal is a system that reads AI news daily and judges what matters to
a small business. Right now it only does the first third of that: it
**collects** items from six sources and **cleans** out exact duplicates.
Nothing reads the content and scores it yet, nothing emails anyone, and
there's no real database — just JSON files sitting in the repo.

Two scripts do all the work: `ingest.py` pulls raw items in, `dedup.py`
removes repeats. A static webpage lets you look at the result in a table.
A scheduled robot (GitHub Actions) runs both scripts once a day
automatically. That's the entire system as of today.

---

## 2. Concepts you'll see everywhere below

**API** — A menu, not a scraped table. Instead of a program reading a
webpage built for human eyes, it sends a request to an address a server has
set aside specifically for programs, and gets back just the data it asked
for. *→ here: every fetch in `ingest.py` is one API call — a URL, some
parameters, a response.*

**JSON** — A plain-text way to write structured data. Curly braces `{ }`
hold labeled fields (like a form), square brackets `[ ]` hold a list of
those. It's the shape nearly every API in this project speaks, in and out.
*→ here: `data/raw_items.json` is literally a JSON array of item-objects,
viewable in any text editor.*

**RSS / Atom feed** — A website's self-published API. A fixed URL that
always serves an XML document listing its most recent posts — title, link,
date, sometimes a summary — meant to be read by software, not browsed.
*→ here: `sources.py`'s `RSS_FEEDS` list is five of these URLs; the
`feedparser` library turns the XML into Python dicts.*

**Git & GitHub** — Git snapshots a folder's history on your machine — each
saved snapshot is a "commit," nothing is silently lost. GitHub is a cloud
host for that history: a shared copy anyone with access can pull, plus
tooling layered on top. *→ here: the shared copy is public — required for
the free tier of GitHub Pages.*

**GitHub Actions & cron** — A robot that only wakes up for a trigger (a
schedule, a manual click, a push) defined in a YAML file. It boots a
temporary Linux machine, runs the listed commands, then shuts down.
`"0 12 * * *"` is cron syntax for "12:00 UTC, every day." *→ here:
`daily-ingest.yml` runs the whole pipeline daily; `ci.yml` runs a sanity
check on every push.*

**GitHub Pages** — Pure static file hosting — nothing executes when someone
visits. It just hands out whichever files are currently committed to the
repo, exactly as they are. *→ here: this is why the public site can't
"live fetch" on reload — nothing runs on a visit, only when Actions runs on
its schedule.*

**CI (Continuous Integration)** — An automatic check on every push that
catches obviously broken code before anyone relies on it. Often narrow in
small projects — a smoke test, not proof the logic is correct. *→ here: see
section 6 — it's currently two very small checks, not a real test suite.*

---

## 3. The mechanism: how data moves and where it ends up

The exact same two scripts run in two completely separate places — your
laptop, and a GitHub-hosted machine — and each produces its **own copy** of
the data. Only one of those copies is what the public actually sees.

```
YOUR MACHINE                          GITHUB'S CLOUD
─────────────                         ───────────────
You — terminal                        GitHub Actions
"python ingest.py                     cron 12:00 UTC
 && python dedup.py"                  or manual Run
      │  runs                               │  runs
      ▼                                     ▼
  ingest.py                             ingest.py
  (pulls sources,                       (same script,
   normalizes, filters)                  GitHub's machine)
      │  writes                             │  writes
      ▼                                     ▼
  raw_items.json                        raw_items.json
                                         (+ 14-day build artifact)
      │  reads                              │  reads
      ▼                                     ▼
   dedup.py                              dedup.py
   (drops repeated URLs)                 (drops repeated URLs)
      │  writes                             │  writes
      ▼                                     ▼
  deduped_items.json                    deduped_items.json
      │                                     │
      ├── fetch() ──────┐                   │
      │                 ▼                   │
      │        frontend/index.html          │
      │        localhost:8000               │
      │        (visible only to you)        │
      │                                     │
      └── git push ─────┐   ┌── git push ───┘
          (MANUAL,       ▼   ▼   (AUTOMATIC,
           easy to forget)          daily)
                    ┌───────────┐        ┌────────────────┐
                    │GitHub repo│──on push──▶ ci.yml       │
                    │data/*.json│        │compile+import   │
                    │(committed)│        │check only       │
                    └─────┬─────┘        └────────────────┘
                          │ serves files
                          ▼
                    GitHub Pages
                          │ static only
                          ▼
                    Public site
                    (anyone, refreshes ~daily)
```

**The gotcha:** the cloud run's output is what the public sees,
automatically, once a day. The local run's output only reaches the public
site if you remember to `git push` — nothing does that for you.

---

## 4. Every file, explained

### The pipeline

**`sources.py`** — config, no logic. Every URL, keyword, and threshold the
pipeline reads from, and nowhere else. Holds `RSS_FEEDS` (5 name/url
pairs), the Hacker News search config (`HN_SEARCH_QUERY="AI"`, minimum 20
points, capped at 30 results), and `RECENCY_DAYS = 30`. Its comment header
doubles as a decision log — which sources were tested and rejected (NVIDIA,
MIT Tech Review, arXiv, Meta/Mistral/Microsoft blogs) and exactly why.

**`ingest.py`** — everything that turns a list of URLs into
`data/raw_items.json`. Never lets one bad source take down the whole run.
- `parsed_time_to_iso()` — converts feedparser's parsed date into one
  consistent ISO 8601 string, the same format for every source.
- `strip_html()` — regex-strips HTML tags out of RSS summaries so the
  frontend isn't rendering raw markup.
- `fetch_rss_feed(name, url)` — one HTTP GET + parse per feed. Never
  raises — logs `[FAIL]`/`[WARN]` and returns `[]` instead.
- `fetch_hn_ai_stories()` — one HTTP GET to HN's Algolia search endpoint —
  keyword search + minimum points, not the noisy "top stories" feed.
- `filter_recent(items, days)` — drops anything older than 30 days; keeps
  undated items instead of silently dropping them, and counts them
  separately.
- `main()` — runs every fetch, filters the combined list, writes
  `data/raw_items.json`, prints per-source counts.

**`dedup.py`** — reads raw, writes `deduped_items.json`. One real function:
`dedup_by_url(items)` — a Python `set()` tracks every URL already seen in a
single pass and drops repeats. Deliberately URL-only, not title-matching —
a real duplicate-title trap was found in early data ("Team Update" reused
as a headline for unrelated posts months apart).

### The viewer

**`frontend/index.html`** — one HTML file, inline CSS/JS, no framework, no
build step. On load it `fetch()`es whichever JSON file is selected and
renders a sortable, filterable table. Never talks to OpenAI/HN/etc.
directly — only to whatever's already on disk. Must be served
(`python -m http.server`) rather than opened by double-click: a bare
`file://` page is blocked by the browser from fetching sibling files (a
real security boundary, CORS) — serving it over `http://localhost:8000`
lifts that restriction.

### The automation

**`requirements.txt`** — `feedparser` + `httpx`, the only two third-party
dependencies. `pip install -r requirements.txt` is what makes this
reproducible on GitHub's machine, not just yours.

**`.github/workflows/ci.yml`** — runs on every push/PR. Two checks:
`python -m py_compile` (files parse as valid Python) and
`import ingest, sources` (every import resolves). Neither runs `main()` or
checks that the output is actually correct.

**`.github/workflows/daily-ingest.yml`** — triggered by
`cron: "0 12 * * *"` (12:00 UTC daily) or a manual click on the Actions
tab. Boots a fresh Ubuntu machine, installs dependencies, runs `ingest.py`
then `dedup.py`, uploads `raw_items.json` as a 14-day downloadable build
artifact, then commits `data/*.json` back into the repo as the
`github-actions[bot]` identity and pushes.

### The record

**`data/raw_items.json` & `deduped_items.json`** — the current "database."
Flat committed files, ~167 KB / 138 items each. Git's commit history is the
only version log until Supabase replaces this with a real table.

**`README.md`** — the repo's front door; GitHub renders it automatically on
the main page. Currently stale — still describes "Phase 2, barebones," no
mention of dedup or the frontend viewer.

**`LEARNING.md`** — dated, first-person notes on what was tried, what
broke, and why each decision landed the way it did.

---

## 5. Two ways this pipeline runs

**Manual:**
1. `.venv/bin/python3 ingest.py` in a terminal.
2. Loops over `RSS_FEEDS`, one HTTP GET per feed, parsed with `feedparser`.
3. One HTTP GET to HN's Algolia search endpoint (keyword "AI", min 20
   points, last 30 days).
4. Every item normalized into the same shape; anything older than 30 days
   dropped.
5. Written to `data/raw_items.json`.
6. `.venv/bin/python3 dedup.py` — reads that file, drops repeat URLs,
   writes `data/deduped_items.json`.
7. `python3 -m http.server` from the repo root, open the frontend — it
   `fetch()`es the JSON and renders the table. Nothing leaves your machine.

**Automated (daily-ingest.yml):**
1. At 12:00 UTC daily — or a manual "Run workflow" click — GitHub boots a
   fresh Ubuntu VM.
2. Checks out the repo, installs Python 3.12 and `requirements.txt`.
3. Runs the *exact same* `ingest.py` and `dedup.py` — GitHub's machine
   instead of yours.
4. `raw_items.json` also uploaded as a downloadable build artifact (kept
   14 days).
5. Commits `data/raw_items.json` + `data/deduped_items.json` into the repo
   as `github-actions[bot]`, and pushes.
6. That push is what GitHub Pages serves — the public site's data
   refreshes once a day, automatically.

---

## 6. How this is actually tested today

Honestly: very lightly. Two automatic checks, both narrow, plus manual
eyeballing.

| Check (in ci.yml)              | Verifies                          | Doesn't verify                         |
|---------------------------------|------------------------------------|------------------------------------------|
| `py_compile ingest.py sources.py` | Files parse as valid Python       | Whether the logic runs or does anything sensible |
| `import ingest, sources`        | Every import resolves              | Whether `main()` succeeds, or output is correct |

No unit tests, no assertions like "dedup actually removes duplicates" or
"the recency filter actually drops old items." Verification so far has
meant running a script and reading its printed counts (e.g. "2,133 pulled,
1,995 dropped, 138 kept") and manually skimming the JSON output. Fine for
scripts this size and this deterministic — won't be enough once Phase 3
(LLM scoring) starts, since scored output can't be eyeballed the way a
duplicate count can. That's what a hand-labeled ground-truth eval set is
for — deliberately not built yet.

---

## 7. Where things stood on 2026-08-13

**Commit history (origin/main):**
1. `63c353b` — Initial barebones ingestion: RSS + Hacker News sources,
   first working `ingest.py`.
2. `a0d5ad0` — Added dedup, the frontend viewer, started committing daily
   data — this is what turned on GitHub Pages.
3. `fa112a9` — "Daily data update 2026-08-12" — the automated bot's first
   scheduled commit, made without anyone touching a keyboard.

**Not yet pushed (this machine only, at time of writing):**
- `ingest.py` — modified
- `sources.py` — modified
- `data/raw_items.json` — modified
- `data/deduped_items.json` — modified
- `LEARNING.md` — modified
- brief PDF — untracked

Concretely: the HN Algolia fix, the 30-day recency filter, the `summary`
field, and Google AI Blog all existed only on this machine at review time.
The public site still reflected the Aug 12 commit — one step behind. This
is the "manual git push" gap shown in the diagram above.

---

*Next build step (tracked separately): wiring real persistence via
Supabase, so this stops being flat JSON files.*
