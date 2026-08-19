# Music Show Wins

Music Show Wins is a small Django community resource for browsing K-pop music
show wins from 2014 onward. Wikipedia is the automated source in this phase.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop (for the PostgreSQL development database)

## Local setup

Copy `.env.example` to `.env`, then install the locked environment and start
PostgreSQL:

```text
copy .env.example .env
uv sync --frozen
docker compose -f docker-compose-db.yaml up -d
uv run python manage.py migrate
```

Restore the tracked, cleaned 2014–2025 domain snapshot into an empty database:

```text
uv run python manage.py restore_bootstrap
```

The restore is atomic, validates all references and expected counts, and refuses
to run when any domain table already contains data. The snapshot restores 6
shows, 292 artists, 882 songs and 2,905 dated wins. It also creates 12 reviewed
legacy discrepancy issues and 33 rejected `legacy_undated` issues for the
aggregate-only Music Core 2016 history. Those issues remain as audit data, not
public dated wins. A different JSON file may be supplied explicitly with
`--input`; local paths do not need to be committed.

Start the temporary Django UI with:

```text
uv run python manage.py runserver
```

The UI provides artist and song leaderboards, artist search and details, and a
dated wins view. It is intentionally small while the backend is being revived.

The Next.js frontend skeleton lives in [`frontend/`](frontend/README.md).
Product design and feature implementation are intentionally pending.

## Wikipedia synchronization

Synchronization runs sequentially through Wikimedia's Action API. It retries
transient failures, sends `maxlag`, checks the page revision before fetching
HTML, and treats the revision as the cache key. The default User-Agent is:

```text
KpopWins/0.1 (https://github.com/badmagick329/musicshowwins/issues)
```

The GitHub Issues page is the public contact channel for this User-Agent. The
default sync target is the current and previous calendar year across active
shows:

```text
uv run python manage.py sync_wikipedia
uv run python manage.py sync_wikipedia --year 2026 --show music-bank
uv run python manage.py sync_wikipedia --year 2024 --year 2025 --show inkigayo
uv run python manage.py sync_wikipedia --dry-run
uv run python manage.py sync_wikipedia --dry-run --format json
uv run python manage.py sync_wikipedia --dry-run --strict
uv run python manage.py approve_wikipedia_source --show music-bank --year 2026
```

Use repeatable `--year` and `--show` options for historical backfills (2014 or
later). `--format text` is the default human-readable report; `--format json`
writes a machine-readable report to stdout only. A complete page is validated
before it is applied atomically. New wins are added with source page and
revision provenance; conflicting winners are quarantined as import issues, and
missing historical rows are reported but never deleted. Exact credited
collaboration names are kept as one artist.

`--dry-run` does not write `ImportRun`, `SourcePage`, `ImportIssue`, revision or
domain data. Use it to review every proposed addition, conflict and missing
legacy win before a real sync. `--strict` exits unsuccessfully whenever source
failures or reconciliation work remains. A real sync is an explicit approval
step after reviewing the dry-run report. New show/year sources are denied by
default; approve one explicitly with `approve_wikipedia_source` after reviewing
its dry-run report. A real sync reports unapproved pages without writing them.
Use `--revoke` to disable a previously approved source. Music Core 2016 is a
known unavailable Wikipedia page; its original aggregate records are retained
as rejected audit issues and are not restored as dated wins.

Production deployment and automated scheduling are out of scope for this phase.

## API

The read-only API is available at:

```text
/api/v1/shows
/api/v1/artists
/api/v1/artists/{id}
/api/v1/songs
/api/v1/songs/{id}
/api/v1/wins
/api/v1/leaderboards/artists
/api/v1/leaderboards/songs
/api/schema/
/api/docs/
```

Collection endpoints use page-number pagination (100 by default) and support
search, artist, song, show, year, date range, ordering, and leaderboard filters
where applicable. Anonymous requests are throttled at 60 per minute.

## Checks

Tests use an isolated in-memory SQLite database; local development and deployed
instances use PostgreSQL.

```text
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

## Deferred work

Donations, accounts, public submissions, production deployment, and scheduled
synchronization are deliberately deferred until the product UI is defined.
