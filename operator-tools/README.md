# KpopWins operator tools

This standalone local project maintains an offline win catalogue, ingests uploads
from configured official YouTube channels, and supports local candidate review. It
does not change the public KpopWins database directly.

For the commands-only workflow, see [WORKFLOW.md](WORKFLOW.md).

## Install

From `operator-tools/`, install the locked Python 3.13 environment:

```console
uv sync --frozen
```

Runtime data defaults to the repository's ignored `.ignore/operator-tools/`
directory. Set `KPOPWINS_OPERATOR_HOME` or `KPOPWINS_API_BASE_URL` to override
the defaults.

Create `.ignore/operator-tools/.env` from `.env.example` and add a local YouTube
Data API v3 key. Process environment variables override this file. The tool never
prints the key.

In Google Cloud, create a project, enable YouTube Data API v3, create an API key,
and restrict that key to the YouTube Data API before placing it in the local file.

## Use

The complete workflow is:

1. Create a Google Cloud project.
2. Enable YouTube Data API v3.
3. Create an API key restricted to that API.
4. Store the key in `.ignore/operator-tools/.env`.
5. Initialize or migrate state with `kpopwins-operator init`.
6. Refresh the local KpopWins catalogue with `refresh-wins`.
7. Resolve the configured handles with `youtube verify-channels`.
8. Review every returned channel title and ID.
9. Save the mappings with `youtube verify-channels --apply`.
10. Run `youtube ingest` over one or more bounded runs.
11. Preview and run local matching.
12. List and inspect candidates individually.
13. Approve selected candidates; reject unsuitable candidates.
14. Run `export-approved`.
15. Import the manifest into local Django for final verification.

The tool reads metadata only: it does not download videos, auto-approve matches,
or write to production.

Initialize local state:

```console
uv run kpopwins-operator init
```

Refresh the complete win catalogue from a local KpopWins API:

```console
uv run kpopwins-operator refresh-wins
```

Resolve the tracked handles and inspect the result before storing it:

```console
uv run kpopwins-operator youtube verify-channels
uv run kpopwins-operator youtube verify-channels --apply
```

`--handle @KBSKpop` limits verification or ingestion to one configured handle.
Handle resolution uses `channels.list(forHandle=...)` and stores the stable channel
ID and uploads playlist ID. The registry is
`official-youtube-channels.toml`; edit it only when an official channel changes.

Ingest uploads, then match them locally against current wins:

```console
uv run kpopwins-operator youtube ingest --max-pages 10
uv run kpopwins-operator youtube match --min-score 75 --dry-run
uv run kpopwins-operator youtube match --min-score 75
```

The initial scan resumes from its last completed page and stops at uploads older
than 1 December 2013. Later runs start at the newest uploads and stop after the
first fully known page. `youtube ingest --restart` discards an initial-scan
checkpoint. Each playlist page and its video details are stored atomically.

List and inspect pending candidates, then make explicit review decisions:

```console
uv run kpopwins-operator candidates list --status pending --min-score 75
uv run kpopwins-operator candidates show 12
uv run kpopwins-operator candidates approve 12 18
uv run kpopwins-operator candidates reject 21
```

Matching uses only locally ingested videos. It requires artist and winner signals,
uses show, song, date, and negative-title evidence for scoring, and never writes a
`no_match` search state. Rejected decisions survive later matching runs.

View local counts or list due work for a provider:

```console
uv run kpopwins-operator status
uv run kpopwins-operator due --provider youtube --limit 100
```

Export approved candidates for current wins:

```console
uv run kpopwins-operator export-approved
```

The default manifest is written to
`.ignore/operator-tools/manifests/win-references-v1.json`. Import it into a local
Django environment from the repository root:

```console
uv run python manage.py import_win_references .ignore/operator-tools/manifests/win-references-v1.json
```

## Reddit wiki audit

The `reddit audit` command performs a read-only audit of the structured
r/kpop music-show wiki. It never creates, updates, approves, or rejects
reference candidates, and it never changes win, search, YouTube ingestion, or
matching state.

Create a Reddit "script" application at <https://www.reddit.com/prefs/apps> and
store its client ID and secret in `.ignore/operator-tools/.env`:

```dotenv
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=KpopWinsOperator/0.1 (audit; by your-reddit-username)
```

`REDDIT_TOKEN_URL` and `REDDIT_API_BASE_URL` default to Reddit's supported OAuth
endpoints and rarely need overriding. All requests use the `client_credentials`
grant with application-only read access; the secret and the access token are
kept in memory and never printed. `reddit audit` fails with a clear message
naming the missing variables when any credential is blank.

Run the audit, then repeat it until it reports `more-remaining=no`:

```console
uv run kpopwins-operator reddit audit --max-pages 100
uv run kpopwins-operator reddit audit --show m-countdown --max-pages 100
uv run kpopwins-operator reddit audit --refresh-indexes --max-pages 100
uv run kpopwins-operator reddit audit --output .ignore/operator-tools/reports/reddit-audit.json
```

Behavior:

- The command reads the r/kpop music-show wiki index and the six show archive
  pages through the OAuth API (`GET /r/kpop/wiki/{page}`); the show slugs map to
  archive paths through the explicit `REDDIT_SHOW_ARCHIVES` mapping in
  `kpopwins_operator/reddit.py`. Edit that constant if Reddit renames an archive.
- Wiki links are normalized across relative, absolute, old-Reddit, and
  current-Reddit forms and deduplicated. Only structured episode pages whose
  final path component is an eight-digit date such as `20240628` are collected;
  ordinary Reddit posts and older non-wiki thread links are ignored.
- Episode pages are cached under `.ignore/operator-tools/reddit/pages/`, and
  crawl state is kept in `.ignore/operator-tools/reddit/state.json`. Repeating
  the command resumes from this cache instead of refetching completed episode
  pages. `--refresh-indexes` refetches the main and show archive pages so later
  runs discover newly added episodes. `--max-pages` limits episode-page network
  requests during one run; cached pages do not count.
- Each episode is matched to the local catalogue only by `show_slug + win_date`.
  The local win remains the source of truth; nothing is inferred from prose.
  The audit reports episodes without local wins and local wins inside a show's
  discovered coverage range that have no episode page.
- For every episode the `WINNER` section is isolated case-insensitively and
  parsing stops at the next Markdown heading. Missing sections, explicit `N/A`,
  winner text without links, and malformed links are separate outcomes.
- Links are classified as `existing_approved`, `existing_pending`,
  `existing_rejected` (matched against local candidates by YouTube video ID
  first, then canonical URL), `new_official` (video already present in
  `youtube_videos`, its channel matches an active `youtube_channels` entry for
  the show, and the local video is active), `known_unavailable` (official and
  locally tracked but currently unavailable), `new_unverified` (any other new
  YouTube link), `unsupported_link` (including Naver and other external
  providers), or `malformed_link`. No Reddit link is treated as proof that a
  video is official, and nothing is auto-approved.
- No YouTube API calls are made. The audit is a lower bound built from metadata
  already collected locally.
- The JSON report defaults to
  `.ignore/operator-tools/reports/reddit-audit.json` with a TSV beside it for
  quick manual inspection. Both are written atomically. Totals are printed after
  every run even while collection is incomplete.

Transient HTTP failures and HTTP 429 responses retry with bounded backoff while
respecting `Retry-After`, and all requests set connection and response timeouts.

## Quota and recovery

The three API methods used here, `channels.list`, `playlistItems.list`, and
`videos.list`, each cost one quota unit per call. Attempted calls are recorded by
Pacific date in SQLite. `YOUTUBE_MAX_API_CALLS_PER_RUN` defaults to 500 and stops a
run before another request exceeds that local ceiling. A YouTube `quotaExceeded`
response stops immediately; resume after the daily Pacific-time reset. HTTP 429
and transient server errors retry up to four attempts and respect `Retry-After`.

If a run fails, fix the cause and rerun it: the last fully stored page remains the
checkpoint. Use `--restart` only when intentionally repeating the initial history
scan. All tests use mocked HTTP responses; the test suite never calls YouTube.
