import Link from "next/link";
import type { Artist } from "@/lib/api";
import { ArtistResults } from "@/components/artist-results";
import { DebouncedArtistSearch } from "@/components/debounced-artist-search";
import { artistsUrl } from "@/lib/artist-list";

export function ArtistSearch({ query, results, resultCount }: { query: string; results: Artist[]; resultCount: number }) {
  return (
    <section id="search" aria-labelledby="artist-search-title" className="border-2 border-foreground bg-search-surface p-5 shadow-[4px_4px_0_var(--section-ink)] sm:p-6">
      <div className="grid gap-5 lg:grid-cols-[0.38fr_1fr] lg:items-end">
        <div>
          <h2 id="artist-search-title" className="font-heading text-2xl font-bold tracking-tight">Find an artist</h2>
          <p className="mt-1 text-sm text-foreground/70">Search by artist name or known alias.</p>
        </div>
        <DebouncedArtistSearch key={query} id="artist-search" query={query} />
      </div>
      {query && (
        <div className="mt-5 border-t-2 border-foreground/25 pt-4">
          <div className="mb-3 flex items-center justify-between gap-4"><p className="text-sm font-semibold">Results for “{query}”</p><span className="text-sm text-foreground/70">{resultCount} {resultCount === 1 ? "artist" : "artists"}</span></div>
          <ArtistResults artists={results} empty="No artists found. Try a shorter or alternate name." />
          {resultCount > results.length && <Link href={artistsUrl({ search: query })} className="mt-4 inline-flex font-bold underline underline-offset-4">View all {resultCount} results</Link>}
        </div>
      )}
    </section>
  );
}
