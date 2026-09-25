# Video reference workflow

Run everything below from the repository root in PowerShell. `operator.ps1`
selects the right Python environment. Agents make the review decisions.

## Routine update

**1. Synchronize and prepare candidates.** Start the local Django API using this
repository's Django settings, then run:

```powershell
./operator.ps1 prepare
```

The launcher first runs `sync_wikipedia` against local Django for the current
and previous years. It uses the same importer as production, including its
source approvals, conflict quarantine and historical-row preservation. A sync
failure stops preparation. Frontend cache refresh is skipped during this step;
the later local reference import refreshes it.

Preparation then refreshes the offline catalogue from
`http://127.0.0.1:8000/api/v1`, ingests official uploads and matches videos.
The launcher overrides `KPOPWINS_API_BASE_URL` for this run even if the operator
`.env` points at production. For another local port, set the process variable
`KPOPWINS_LOCAL_API_BASE_URL`. The API must use the same Django settings and
database as the launcher. Both the source endpoint and local target are printed.
Direct `kpopwins-operator prepare` remains an offline command using its configured
API; use `operator.ps1 prepare` for the synchronized local workflow.

To synchronize separately or repair older missing wins:

```powershell
./operator.ps1 sync-local
./operator.ps1 sync-local --year 2024
```

Review any reported conflicts or unapproved source pages. Sync does not invent
wins or override those decisions. Preparation stops if approved reference wins
are absent from the refreshed catalogue, preserving the previous offline state.

Add `--reddit` to also audit Reddit, fetch missing YouTube metadata,
reclassify links and import official links as pending candidates:

```powershell
./operator.ps1 prepare --reddit
```

If discovery pauses, repeat the same command. Completed pages are saved. The
YouTube request budget is shared across ingestion and Reddit hydration. Default
limits are 10 upload pages per channel and 100 Reddit episode pages. Override
with `--max-pages` and `--reddit-max-pages`. YouTube quota exhaustion requires
waiting for its reset. Candidates already found can be reviewed during backfill.
At the end, `prepare` reports new candidates created, candidates that were already
pending, the ready/deferred review queue, and official links withheld because
their episode has no local win. When discovery completes with no new or ready
candidates, it says to continue with `export-approved` instead of sending you to
another review batch. The same counts are saved in
`.ignore/operator-tools/reports/prepare.json`.

**2. Required agent handoff.** Do not fill `decisions.json` yourself when using
an agent reviewer. `review batch` creates an evidence file and an unfilled agent
output template; neither creating the batch nor applying the blank template
performs a review. Give the printed paths and handoff prompt to Luna or another
review agent.

Ask an agent to review the next batch. Copy this message into a task in
this project. Reuse it unchanged each time; the agent selects the batch and
handles its file paths:

```text
Review and apply the next batch of YouTube video candidates in this project.

Follow .ignore/docs/operator-workflow/agent-review-playbook.md. Run
./operator.ps1 review batch to create or resume an assignment. Read every
candidate in the batch.json file printed as Agent evidence, check the evidence,
and fill decisions.json with approve, reject or defer decisions, your reviewer
identity, and specific reasons and evidence.

Apply the completed file through ./operator.ps1 review apply. If the batch is
stale, cancel it, create a fresh batch and review the current evidence. Stop
after one batch and report approved, rejected and deferred counts, with reasons
for unresolved cases. If no candidates are ready, report that and stop.
Do not export references, import into Django or contact production.
```

You can use this prompt in the current task or give it to another agent working
in this repository. The [agent playbook](../.ignore/docs/operator-workflow/agent-review-playbook.md)
contains the review criteria and recovery instructions.

Each batch gets a generated ID, such as `bbf708c4630446348e893f2a8e428bd9`.
That ID is the name of its subfolder inside `.ignore/operator-tools/reviews`:

```text
.ignore/operator-tools/reviews/
  bbf708c4630446348e893f2a8e428bd9/
    batch.json       # Evidence the agent reads
    decisions.json   # Decisions the agent fills in
    applied.json     # Log created after applying decisions
```

There is no directory literally named `batch`. The output prints full paths
to `batch.json` and `decisions.json` inside the batch-ID subfolder.

The batch includes up to 25 candidates, latest wins first, with video metadata,
official-channel mappings, matching evidence, cached Reddit winner text and
other candidates for the same win.

The agent fills `decisions.json` with approve, reject or defer, plus its identity,
reason and specific evidence for each candidate. Blank templates cannot be applied.

**3. Check the agent's result.** The prompt above includes applying the decisions;
you do not need to run a separate command. The agent uses:

```powershell
./operator.ps1 review apply ".ignore/operator-tools/reviews/<batch-id>/decisions.json"
```

The whole batch is validated and saved atomically. Add `--dry-run` for validation
only. `applied.json` records the result; the database retains the decision history.
Rerunning the same applied file is harmless.

Reuse the same prompt for the next batch. Deferred candidates remain pending but are skipped until
their evidence changes. Use `review batch --include-deferred` to reconsider them.

**4. Finish ready reviews, then export, verify and import locally.** Follow the
queue printed after `review apply`. If ready candidates remain, give another
batch to the agent. Deferred candidates are skipped until evidence changes or
you explicitly include them. When no ready candidates remain, run these commands
in order:

```powershell
./operator.ps1 export-approved
./operator.ps1 verify
./operator.ps1 import
```

Export writes the full approved manifest, not an incremental patch. `verify`
requires that exported file and dry-runs it against local Django. If wins are
missing, it reports target coverage and every missing show/date together. Run
`sync-local` for those years, resolve source issues, then verify again. Do not
remove approved references merely to pass validation. Local verification checks
local Django only; the production dry run in step 5 checks production separately.

`verify` makes no database writes; `import` applies it using the
repository's Django settings and then tries to refresh the frontend cache. If
the local frontend is not running, the references are still imported and the
command prints a warning that local cache refresh was skipped. Start the
frontend and rerun `uv run python manage.py refresh_public_cache` when you want
to warm the local pages.

**5. Import the same manifest into production.** A local import updates only the
database configured in your local Django settings. Deploying application code
does not copy that database or the ignored manifest to production.

From the repository root, validate against the running production backend:

```powershell
./.ignore/deployment/import-win-references.ps1
```

Check the production dry-run counts, then apply:

```powershell
./.ignore/deployment/import-win-references.ps1 -Apply
```

The helper repeats validation and streams the manifest to the running backend.
The import refreshes the public cache. Check the affected wins on the public site.
Routine video updates need no new deployment. Deploy backend changes and their
migrations first when required, such as support for withdrawn references.
See [the deployment runbook](../.ignore/deployment/runbook.md) for code releases.
Exported files stay ignored and are never included in the application image.

## Resume or narrow review

- `review batch` resumes an open batch for the same filters without replacing
  the agent's decision file.
- `review status` lists open batch IDs and their subfolder paths inside `reviews`.
- `review cancel <batch-id>` releases an abandoned or stale batch. Then create
  a fresh batch. Previous decisions are unchanged.
- `review batch --show music-bank` or `--source reddit_audit` narrows selection.
  The other source is `youtube_match`. `--limit 10` makes a smaller batch.
- If apply reports changed evidence, cancel and regenerate the batch, then
  review it again. Editing the exported evidence file cannot bypass this check.

## First-time setup

1. Install with `uv sync --project operator-tools --frozen`.
2. Create `.ignore/operator-tools/.env` from `operator-tools/.env.example` and
   supply the YouTube API key. Reddit credentials are needed only with `--reddit`.
3. Run `./operator.ps1 init`, then `./operator.ps1 youtube verify-channels`.
   Check the resolved channels, then run
   `./operator.ps1 youtube verify-channels --apply` to save them.
4. Start the local Django API. Apply Django migrations after updating backend code.

`prepare` and `review` automatically initialize or migrate offline operator
state. Channel verification remains explicit. For later runs, go straight to
`prepare`; initial history scanning uses the same resumable command.

## Correct a published reference

```powershell
./operator.ps1 candidates withdraw 12 --reviewer agent-name --reason "Wrong episode confirmed"
```

Export and import afterward to withdraw it from Django. Rejection or omission
alone does not remove a published reference. Withdrawals survive rematching.
Restoration requires an explicitly reviewed `candidates approve 12 --revise`
with `--reviewer` and `--reason`, followed by another export/import.

Artist or song corrections during catalogue refresh return previous approvals
to pending. Review them again; explicitly withdraw any published reference found
wrong. Use `candidates show <id>` to inspect its review history.
