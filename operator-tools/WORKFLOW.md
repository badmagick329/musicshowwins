# Operator workflow

Run these commands from `operator-tools/`.

## One-time setup

```console
uv sync --frozen
uv run kpopwins-operator init
uv run kpopwins-operator refresh-wins
uv run kpopwins-operator youtube verify-channels
uv run kpopwins-operator youtube verify-channels --apply
```

Review the channel names printed by `verify-channels` before using `--apply`.

## Initial YouTube backfill

```console
uv run kpopwins-operator youtube ingest --max-pages 10
```

Repeat that command until it reports `more-remaining=no`. Progress is saved after
each page. If YouTube reports exhausted quota, continue the next day.

Match the downloaded videos after the backfill finishes:

```console
uv run kpopwins-operator youtube match --dry-run
uv run kpopwins-operator youtube match
```

## Review candidates

```console
uv run kpopwins-operator candidates list --status pending --limit 100
uv run kpopwins-operator candidates show 12
uv run kpopwins-operator candidates approve 12 18
uv run kpopwins-operator candidates reject 21
```

Replace the example IDs with the candidates you reviewed. Keep listing pending
candidates until none remain.

## Audit the r/kpop wiki (read-only)

```console
uv run kpopwins-operator reddit audit --max-pages 100
```

Repeat that command until it reports `more-remaining=no`. Cached episode pages
are reused, so reruns resume instead of refetching. Use `--refresh-indexes`
after new episodes are added on Reddit and `--show <slug>` to scope one show.
Then review the JSON/TSV report under `.ignore/operator-tools/reports/`. This
command does not create, update, approve, or reject candidates; importing
Reddit results is a later task.

## Export and test locally

```console
uv run kpopwins-operator export-approved
```

This writes `.ignore/operator-tools/manifests/win-references-v1.json`. From the
repository root, import it into local Django:

```console
uv run python manage.py import_win_references .ignore/operator-tools/manifests/win-references-v1.json
```

Do not commit the manifest.

## Import approved references into production

The host-specific import helper lives in the ignored deployment directory. From
the repository root, run its production dry run:

```powershell
./.ignore/deployment/import-win-references.ps1
```

If the dry run passes, import the same manifest:

```powershell
./.ignore/deployment/import-win-references.ps1 -Apply
```

The helper streams the manifest into the running backend. It does not copy the
file onto the server. See `.ignore/deployment/runbook.md` for the private details.

## Later updates

For later runs, refresh the wins, ingest new uploads, match them, review the new
candidates, and export again:

```console
uv run kpopwins-operator refresh-wins
uv run kpopwins-operator youtube ingest --max-pages 10
uv run kpopwins-operator youtube match --dry-run
uv run kpopwins-operator youtube match
```

Do not rerun `init`, channel verification, or `--restart` unless the local schema
or official channel registry changes.
