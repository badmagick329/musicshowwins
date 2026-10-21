# Frontend

Public Next.js frontend for the KpopWins archive (home, artists, songs, wins,
shows, rankings and about pages), backed by the read-only Django API. See
[`style.md`](style.md) for the product direction.

## Stack

- Next.js 16.3 with the App Router and TypeScript
- Tailwind CSS 4
- shadcn/ui (Base UI, neutral CSS-variable theme)
- TanStack Query for interactive browser-side archive data
- pnpm

## Local development

```text
pnpm install
# copy .env.example to .env.local when the Django API is not on its default URL
pnpm dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

## Data boundary

Route rendering and metadata use the server-side Django API URL. Interactive
archive views use TanStack Query in the browser through the same-origin
`/backend-api` proxy, so the Django URL is never bundled for browsers.

SSR, metadata, sitemap and browser GETs share successful JSON cached
by canonical upstream URL for 24 hours under `public-archive`. The cache strips
unknown parameters, normalizes supported values and rejects malformed or
oversized inputs before fetching. Backend failures, including 429, are uncached.
Public misses carry `X-KpopWins-Public-Read: 1` with the internal key, so Django
applies its shared 600-read/minute database budget. Cached responses remain
usable after exhaustion. The authenticated revalidation warmer uses a private
server context to fill the same entries without consuming the public budget.
Numeric artist redirects use uncached public reads with the same budget marker;
Next Proxy runs in a separate cache runtime.
The reader's explicit `archive-json-v2` identity is stable across compiled entry
bundles. Bump its version when cache semantics change. The production-image CI
probe checks real cross-entry reuse, warming and 429 recovery with a local stub.
Cache refresh is two authenticated POSTs: `/api/revalidate?action=invalidate`,
then `/api/revalidate?action=warm`. Invalidation must finish first because Next
flushes it at request completion; warming in that request would expire new data.

POST is supported only for corrections, with a 32 KiB cap checked against both
declared length and streamed bytes. Excess input is cancelled and returns 413
without a Django request; valid-sized input retains Django validation/throttling.

`/wins` is the public archive browser. It supports text, show, year, date,
ordering, and page filters with shareable URLs.

## Checks

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
