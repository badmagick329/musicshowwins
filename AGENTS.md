# Repository instructions

- Put agent-created documents under `./.ignore/docs`; follow its `README.md` for placement and lifecycle. Keep the docs root for the index only.
- For public UI changes, follow `frontend/style.md`.
- Preserve exact credited collaboration names as one artist. Keep undated aggregate history out of dated wins; quarantine conflicting imported winners and retain historical rows missing from a source.
- Edit notable moments in `musicshowwins/main/data/artist_moments_pilot.json`. Deployment sync treats copy, citations, and publication status as authoritative; use `draft` to withdraw a moment, not omission. Keep pending catalogue matches unpublished.
- Verify moment claims against article bodies. Distinguish career-first from song-first or show-first wins; catalogue order alone does not establish a career-first. Prefer meaningful sourced context over routine results or score recaps.
- Keep `operator-tools` offline from public database writes: reviewed references reach Django through exported manifests, not automatic candidate approval or direct production writes.
- For deployment work, read `.ignore/deployment/runbook.md`. Production orchestration stays outside version control; building/loading an image and deploying it are separate steps. Keep pre-start content sync independent of frontend availability; refresh caches after readiness.
