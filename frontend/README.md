# Frontend

Next.js frontend for the Music Show Wins archive. The homepage is a first live
vertical slice backed by the read-only Django API; see [`style.md`](style.md)
for the product direction.

## Stack

- Next.js 16.3.1 with the App Router and TypeScript
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
`/backend-api` rewrite, so the Django URL is never bundled for browsers.

`/wins` is the public archive browser. It supports text, show, year, date,
ordering, and page filters with shareable URLs.

## Checks

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
