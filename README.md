# DeeperApps AI Signal Pipeline

Reads AI industry news daily, judges what actually matters to an SMB and to
DeeperApps, and (eventually) delivers that as a short brief plus a queryable
history. Internal training project — see the project brief for full context.

## Status

Phase 3 (Storage + Viewer). Pulls raw items from Tier 0 sources (vendor RSS
feeds + Hacker News) via `ingest.py`, dedupes them via `dedup.py`, and
persists them two ways: `data/*.json` files (committed to the repo, and what
the frontend reads from) and a real Postgres database on Supabase (the
source of truth going forward). A browser-based viewer
(`index.html`, live at https://aarony13.github.io/deeperapps-signal-pipeline/)
lets you sort/search/filter the collected items, including a heuristic
"could be SMB-relevant" keyword filter. No real relevance scoring yet —
that's Phase 4.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

To write to Supabase locally, create a `.env` file (gitignored) in the repo
root with:

```
SUPABASE_URL=your-project-url
SUPABASE_SERVICE_KEY=your-service-role-key
```

This is optional — without it, `ingest.py` still writes the JSON files as
normal and just skips the Supabase step.

## Run

```bash
.venv/bin/python3 ingest.py
.venv/bin/python3 dedup.py
```

Then open `index.html` (or serve the repo root with
`python3 -m http.server`) to browse the results.

## CI/CD

- `.github/workflows/ci.yml` — sanity-checks the code on every push/PR.
- `.github/workflows/daily-ingest.yml` — runs ingestion + dedup daily,
  writes to Supabase using the `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`
  repo secrets, commits the updated JSON files back to the repo, and
  uploads the raw output as a build artifact. Also runnable manually
  from the Actions tab.
