import type { Metadata } from "next";
import Link from "next/link";
import { ArtistResults } from "@/components/artist-results";
import { DebouncedArtistSearch } from "@/components/debounced-artist-search";
import { ArchiveResultsSummary, Pagination } from "@/components/pagination";
import { getArtists, parsePositivePage } from "@/lib/api";
import { artistSortLabels, artistSorts, artistsUrl, parseArtistSort } from "@/lib/artist-list";
import { noIndexFollow, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";
const description = "Find artists by name or win total, then view their songs and full win history.";
type ArtistsSearchParams = { search?: string | string[]; page?: string | string[]; sort?: string | string[] };

export async function generateMetadata({ searchParams }: { searchParams: Promise<ArtistsSearchParams> }): Promise<Metadata> {
  const params = await searchParams;
  const search = typeof params.search === "string" ? params.search.trim() : "";
  const page = parsePositivePage(params.page);
  const sort = parseArtistSort(params.sort);
  const canonical = !search && page > 1 ? `/artists?page=${page}` : "/artists";
  return {
    ...pageMetadata({ title: page > 1 && !search ? `Artists, page ${page}` : "Artists", description, path: canonical }),
    robots: search || sort !== "wins" ? noIndexFollow : undefined,
  };
}

export default async function ArtistsPage({ searchParams }: { searchParams: Promise<ArtistsSearchParams> }) {
  const params = await searchParams;
  const search = typeof params.search === "string" ? params.search.trim() : "";
  const page = parsePositivePage(params.page);
  const sort = parseArtistSort(params.sort);
  const artists = await getArtists(search, page, sort);

  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
        <h1 className="font-heading text-4xl font-bold tracking-tight">Artists</h1>
        <p className="mt-2 max-w-2xl text-surface-berry-foreground/80">Find an artist and view their winning songs and full win history.</p>
      </header>
      <div className="mt-8 border-2 border-foreground bg-search-surface p-5">
        <DebouncedArtistSearch id="artist-list-search" query={search} />
      </div>
      <section className="mt-7" aria-labelledby="artist-sort-title">
        <div className="flex flex-col gap-3 border-b-2 border-foreground pb-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="artist-sort-title" className="font-heading text-lg font-bold">Sort artists</h2>
          <nav aria-label="Artist sorting" className="grid grid-cols-3 border-2 border-foreground bg-card">
            {artistSorts.map((option) => (
              <Link
                key={option}
                href={artistsUrl({ search, sort: option })}
                aria-current={sort === option ? "page" : undefined}
                className={`border-r-2 border-foreground px-3 py-2 text-center text-sm font-bold last:border-r-0 ${sort === option ? "bg-brand-pink text-white" : "hover:bg-accent"}`}
              >
                {artistSortLabels[option]}
              </Link>
            ))}
          </nav>
        </div>
      </section>
      <section className="mt-8" aria-labelledby="artist-results-title">
        <div className="mb-4 flex items-end justify-between gap-4 border-b-2 border-foreground pb-3">
          <h2 id="artist-results-title" className="scroll-mt-24 font-heading text-2xl font-bold">{search ? `Results for "${search}"` : "All artists"}</h2>
          <ArchiveResultsSummary totalCount={artists.count} page={page} resultCount={artists.results.length} singular="artist" plural="artists" />
        </div>
        <ArtistResults artists={artists.results} empty={search ? "No artists found. Try a shorter or alternate name." : "No artists are available right now."} />
        <Pagination page={page} totalCount={artists.count} hasPrevious={Boolean(artists.previous)} hasNext={Boolean(artists.next)} search={search} sort={sort} />
      </section>
    </main>
  );
}
