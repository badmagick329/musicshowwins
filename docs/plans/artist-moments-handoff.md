# Implement the artist moments pilot

## Objective

Add sourced stories about individual music show wins to the public Next.js app. Deliver code and locally reviewable content for six artists: CORTIS, aespa, BTS, IVE, Red Velvet and T-ara. The planning agent reviews the result; deployment and production content import are separate actions.

Read `AGENTS.md`, then `docs/research/artist-moments-pilot.md` before implementation. That research file is the source of truth for pilot copy, event identities, citations and unresolved evidence. Use aespa's revised blurb, which supersedes its original draft. Implement the six main stories; additional candidates remain outside this release.

## 1. Match the pilot content

Resolve each event against available catalogue data using show and event date, verifying the credited artist and song. Record resolved IDs and normalized names in a matching report. Use portable event identities in committed seed content, since database IDs can differ between environments.

The bundled snapshot covers 2014–2025; CORTIS's 2026 event may be absent. If an event is missing or mismatched, keep that content pending and report it explicitly. Complete the feature and test it with isolated fixtures. Follow the existing source-approval workflow for any requested catalogue additions; never invent a win or silently match a nearby date.

For aespa, the text-supported absence and hosts filling the encore are sufficient for this release. The precise dance description and any COVID explanation remain excluded unless you directly verify supporting evidence. An unwatched video is a research lead, not a verified reference. Prefer an existing verified video for the exact win; a video is optional for a story.

Done when all six entries are classified as matched or pending with a specific reason, and every sentence of selected copy has a supporting citation.

## 2. Store stories and citations

Use a small dedicated `WinMoment` model with one story per win: unique win relationship, heading, plain-text body, draft/published status, timestamps and relationships to supporting `WinReference` records. Derive artist, song, show and date through the win. Reuse existing article references and their publisher/title/URL metadata.

Require at least one active article citation before publishing. Enforce that every selected citation belongs to the same win. Keep these checks effective for both the content import path and Django admin. Expose a simple admin editing workflow. Source removal or unavailability must leave the public story hidden when it has no active citations; never expose an unsupported story.

Provide a committed pilot content file and a repeatable import command with a dry run. Validate each entry before mutation; fail on malformed, mismatched or unresolved selected entries. Support selecting a subset so explicitly pending entries do not prevent importing matched ones. Import selected entries atomically and upsert by event identity, preserving unrelated references. Repeating the same import produces no duplicates. Document the actual invocation and matching outcome.

Default imported stories to draft; support an explicit publication step after validation. Use publication dates only when accurately known; existing reference datetimes may remain null when only a calendar date is known. Never fabricate a time or timezone from an article's displayed date.

Done when the six stories have a reproducible content path, validation is shared across supported writes, and draft/public state can be reviewed locally.

## 3. Expose and display moments

Expose the optional public moment with each win through the existing API and frontend types. Include heading, body and active selected citation metadata. Prefetch relationships so query count does not grow with the number of wins. Follow existing public-archive cache invalidation for imports and admin edits, including publication, unpublication and changes to supporting references. Invalidate after committed mutations; report callback failures accurately.

On artist pages, render a `Notable moments` section after Summary and before the show/song breakdown. Each story shows a descriptive heading, event date, linked song, show, short body and visible article links with publisher labels. For the first-win entries, use headings such as `aespa's first music show win` that state what visitors are looking for. Order moments chronologically, oldest first.

On song pages, render the same shared story component before Win history, restricted to that song. Render one copy of each story per page. Give the corresponding win-history record a stable anchor so a story can link to that exact win. Reuse the established video interaction for the win, clearly distinguishing article links from video actions. Only describe a link as a winner announcement or encore when that specific video has been verified as such.

Use existing typography, spacing, colors and responsive conventions from `frontend/style.md`. Keep story text and citations in server-rendered HTML. Omit the entire section on pages without public moments. Keep internal review notes, verification status and import details out of public copy.

Scope excludes charts, bulk article discovery, standalone story URLs, general song background stories, new analytics and changes to the temporary Django public templates.

Done when matched pilot stories can be reviewed on both artist and song pages and the existing archive/video interactions still work.

## 4. Verify and return for review

Add meaningful tests covering: wrong-event rejection; same-win citation validation; draft exclusion; no-active-citation exclusion; idempotent imports; dry runs without writes; publication and cache invalidation; bounded API queries; correct artist/song filtering; source links and win anchors; pages without moments. Test the API-to-page behaviour rather than only component internals.

Run the repository's relevant backend and frontend checks using the current documented scripts. Visually inspect desktop and mobile pages, including T-ara's two-source story, aespa's revised story, a page without stories and a story without video. Check keyboard access and wrapping of long source titles.

Return a change summary, matching/import report for all six artists, checks and results, screenshots or local review URLs, and any unresolved records or evidence. Identify separately what is implemented, what content is locally reviewable, and what is still pending. The implementation is ready for planning-agent review once these artifacts are available; production release is outside this handoff.

## Code entry points

Inspect the current files before editing; these pointers locate the existing mechanisms rather than prescribing every file change:

- `musicshowwins/main/models.py`, `admin.py`, `win_reference_io.py`, `cache_invalidation.py`, `services.py`.
- `musicshowwins/restapi/serializers.py` and `views.py`.
- `frontend/src/lib/api-shared.ts` and `api.ts`.
- `frontend/src/app/artists/[id]/page.tsx` and `frontend/src/app/songs/[id]/page.tsx`.
- `frontend/src/components/artist-win-history.tsx`, `win-videos.tsx` and `data-display.tsx`.
