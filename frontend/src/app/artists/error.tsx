"use client";

export default function ArtistsError({ reset }: { error: Error; reset: () => void }) {
  return <main className="mx-auto max-w-7xl px-5 py-10 lg:px-8"><div role="alert" className="border border-border border-l-4 border-l-warning bg-card p-5"><h1 className="font-heading text-2xl font-bold">Artists couldn&apos;t load.</h1><p className="mt-2 text-muted-foreground">Your search and sort settings are unchanged.</p><button onClick={reset} className="mt-4 border-2 border-foreground bg-highlight-yellow px-4 py-2 font-bold">Try again</button></div></main>;
}
