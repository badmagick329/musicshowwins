# Artist moments review fixes

Scope: fix the findings below, then return for review. Preserve the agreed pilot content. This review inspected the diff and added tests, and ran isolated in-memory reproductions for admin validation, bulk deletion, invalid URLs and pending selections. It did not rerun the general suite or perform browser QA.

## Required fixes

1. **Validate submitted admin citations before saving.** `main/admin.py:35-38` validates after saving M2M relations, while `WinMoment.clean()` inspects the previously stored relations during form validation. Reproduced: adding a valid citation and publishing a citation-free draft in one submission produces a false validation error; selecting a wrong-win citation passes form validation and then raises an uncaught `ValidationError` during save. Validate the submitted relation set in the admin form, share the domain checks with the importer, and preserve transactional writes. Done when valid publication succeeds in one submission and invalid selections display form errors without HTTP 500 or partial writes. Also allow correcting a published story whose last citation became unavailable.

2. **Cover all supported admin mutations with cache invalidation.** `WinReferenceAdmin.delete_model()` does not handle Django's bulk-delete action. Reproduced bulk deletion of a published story's only citation with zero invalidation callbacks. Inline reference edits through WinAdmin also bypass WinReferenceAdmin hooks, and WinMoment deletion has no invalidation hook. These paths leave removed or unsupported stories in the public cache until expiry. Cover direct and bulk story deletion, direct and bulk reference deletion, and inline reference changes after commit. Done when targeted tests demonstrate those changes invalidate the cached public representation and rollbacks do not trigger callbacks.

3. **Make the win anchor work on mobile.** `win-moments.tsx:21` always links to `#win-ID`, which exists only on the desktop table cell in `artist-win-history.tsx:14`. Mobile hides that table and exposes `#win-mobile-ID` instead. Route the action to the visible record at both breakpoints without duplicate IDs. Done when clicking View this win on desktop and mobile visibly reaches the matching record and its existing video controls.

4. **Validate the complete import document before reporting success.** `moment_io.py:55-61` checks only truthiness of some citation fields. Reproduced: URL `not a URL` passes dry run and is stored as a citation on a published story. Missing provider passes dry run but fails on the real import. Validate object shapes, required string types, lengths, and HTTP(S) URLs using the existing reference validation conventions; convert failures to entry-specific document errors. Apply equivalent validation in dry run and real import. Also resolve explicit artist selections before filtering state: selecting a pending artist currently reports success with zero entries. Done when malformed selected entries fail without writes, dry run predicts validation failures, and explicitly selected pending or unknown artists produce actionable errors.

## Small handoff gaps

- Move song-page Notable moments before Win history as specified; it is currently after the history.
- Distinguish same-publisher citations visibly. BTS and T-ara currently each show two indistinguishable Soompi links because article titles are screen-reader-only. Show concise article labels alongside publisher names.
- Correct the matching report command: the repository's `manage.py` is at its root. Report actual resolved IDs separately from portable seed identities, and state the catalogue/environment used. Include targeted check results and the desktop/mobile review evidence; the current report only lists matches.

Return the changed files, targeted regression results for these findings, and browser evidence for the mobile anchor and story placement. Reuse prior general check results where still applicable; run affected checks after the fixes. Keep unresolved CORTIS content explicitly pending unless the real catalogue now provides a verified matching event.
