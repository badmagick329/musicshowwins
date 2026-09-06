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
uv run kpopwins-operator candidates approve 12 18 --reviewer agent-name --reason "Exact show, winner and episode confirmed"
uv run kpopwins-operator candidates reject 21 --reviewer agent-name --reason "Wrong episode confirmed"
```

Replace the example IDs with the candidates you reviewed. Continue through the queue; leave uncertain candidates pending.

## Audit the r/kpop wiki (read-only)

```console
uv run kpopwins-operator reddit audit --max-pages 100
```

Repeat that command until it reports `more-remaining=no`. Cached episode pages
are reused, so reruns resume instead of refetching. Use `--refresh-indexes`
after new episodes are added on Reddit and `--show <slug>` to scope one show.
Once the audit reports complete collection, hydrate the unverified YouTube links:

```console
uv run kpopwins-operator reddit hydrate-youtube
```

Repeat hydration until it reports `more-remaining=no`, then rerun the audit to
reclassify links using the downloaded metadata:

```console
uv run kpopwins-operator reddit audit --max-pages 100
```

Review the refreshed JSON/TSV report under `.ignore/operator-tools/reports/`.
Preview and import the official links as pending candidates, then review them:

```console
uv run kpopwins-operator reddit import-official --dry-run
uv run kpopwins-operator reddit import-official
uv run kpopwins-operator candidates list --status pending --provider youtube
```

Audit and hydration do not change candidates. Importing never approves a
candidate or overwrites an existing review decision.

## Correct a previous decision

Approve/reject require `--reviewer` and `--reason`; group only candidates sharing
that reason. Add `--revise` when deliberately changing a previous review. History
is stored locally and displayed by `candidates show`.

For a reference that should be removed from the public site, use an explicit
withdrawal, then export and import the manifest through the normal steps:

```console
uv run kpopwins-operator candidates withdraw 12 --reviewer agent-name --reason "Wrong episode confirmed"
```

Rejecting or omitting a candidate does not remove an imported reference.
Withdrawals survive rematching. Restoring one requires `approve --revise` after
review, followed by another manifest import.

After upgrading to schema 4, run `uv run kpopwins-operator init` once. Winner
artist/song corrections during `refresh-wins` return approvals to pending and
record why. Review them again before export. Existing public references require
an explicit withdrawal if the review establishes they are wrong.

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
