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

Restore the tracked 2014–2025 domain snapshot into an empty database:

```text
uv run python manage.py restore_bootstrap
```

The restore is atomic, validates all references and expected counts, and refuses
to run when any domain table already contains data. Start the temporary Django
UI with:

```text
uv run python manage.py runserver
```

The UI provides artist and song leaderboards, artist search and details, and a
dated wins view. It is intentionally small while the backend is being revived.

## Wikipedia synchronization

Synchronization runs sequentially through Wikimedia's Action API. It sends a
descriptive User-Agent and `maxlag`, checks the page revision before fetching
HTML, and treats the revision as the cache key. The default is the current and
previous calendar year across active shows:

```text
uv run python manage.py sync_wikipedia
uv run python manage.py sync_wikipedia --year 2026 --show music-bank
uv run python manage.py sync_wikipedia --year 2024 --year 2025 --show inkigayo
uv run python manage.py sync_wikipedia --dry-run
```

Use repeatable `--year` and `--show` options for historical backfills (2014 or
later). A complete page is validated before it is applied atomically. New wins
are added with source page and revision provenance; conflicting winners are
quarantined as import issues, and missing historical rows are reported but
never deleted. Exact credited collaboration names are kept as one artist.

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

Next.js, donations, accounts, public submissions, production deployment, and
scheduled synchronization are deliberately deferred until the backend and
temporary UI are stable.
