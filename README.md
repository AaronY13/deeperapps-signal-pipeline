# DeeperApps AI Signal Pipeline

Reads AI industry news daily, judges what actually matters to an SMB and to
DeeperApps, and (eventually) delivers that as a short brief plus a queryable
history. Internal training project — see the project brief for full context.

## Status

Phase 2 (Ingestion) — barebones. Pulls raw items from Tier 0 sources
(vendor RSS feeds + Hacker News) into `data/raw_items.json`. No dedup,
scoring, or storage yet.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python3 ingest.py
```

## CI/CD

- `.github/workflows/ci.yml` — sanity-checks the code on every push/PR.
- `.github/workflows/daily-ingest.yml` — runs the ingestion script daily
  and uploads the output as a build artifact. Also runnable manually from
  the Actions tab.
