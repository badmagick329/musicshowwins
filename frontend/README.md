# Frontend

Next.js frontend for the Music Show Wins archive. The homepage is a first live
vertical slice backed by the read-only Django API; see [`style.md`](style.md)
for the product direction.

## Stack

- Next.js 16.3.1 with the App Router and TypeScript
- Tailwind CSS 4
- shadcn/ui (Base UI, neutral CSS-variable theme)
- pnpm

## Local development

```text
pnpm install
# copy .env.example to .env.local when the Django API is not on its default URL
pnpm dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

## Checks

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
