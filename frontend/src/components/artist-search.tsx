import type { Artist } from "@/lib/api";
import { EmptyState } from "@/components/data-display";

export function ArtistSearch({ query, results }: { query: string; results: Artist[] }) {
  return (
    <section
      id="search"
      aria-labelledby="artist-search-title"
      className="border-2 border-foreground bg-search-surface p-5 shadow-[4px_4px_0_var(--section-ink)] sm:p-6"
    >
      <div className="grid gap-5 lg:grid-cols-[0.38fr_1fr] lg:items-end">
        <div>
          <h2
            id="artist-search-title"
            className="font-heading text-2xl font-bold tracking-tight"
          >
            Find an artist
          </h2>
          <p className="mt-1 text-sm text-foreground/70">
            Search by artist name or known alias.
          </p>
        </div>
        <form action="/" method="get" className="flex flex-col gap-3 sm:flex-row">
          <label htmlFor="artist-search" className="sr-only">
            Artist name or alias
          </label>
          <input
            id="artist-search"
            name="search"
            defaultValue={query}
            placeholder="Artist name or alias"
            className="min-h-12 min-w-0 flex-1 border-2 border-foreground bg-card px-4 text-base placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            className="min-h-12 border-2 border-foreground bg-brand-pink px-6 font-bold text-white shadow-[3px_3px_0_var(--foreground)] transition-transform hover:-translate-y-0.5"
          >
            Search
          </button>
        </form>
      </div>
      {query && (
        <div className="mt-5 border-t-2 border-foreground/25 pt-4">
          <p className="mb-3 text-sm font-semibold">
            Results for “{query}”
          </p>
          {results.length ? (
            <ul className="divide-y divide-border border-2 border-foreground bg-card">
              {results.map((artist) => (
                <li
                  key={artist.id}
                  className="flex items-center justify-between gap-4 px-3 py-3"
                >
                  <span className="font-semibold">{artist.name}</span>
                  <span className="text-sm tabular-nums text-muted-foreground">
                    {artist.total_wins ?? 0} wins
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="No artists found. Try a shorter or alternate name." />
          )}
        </div>
      )}
    </section>
  );
}
