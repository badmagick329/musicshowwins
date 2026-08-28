import { ArtistSearch } from "@/components/artist-search";
import {
  ErrorState,
  Leaderboard,
  MusicShowList,
  RecentWins,
  SectionHeading,
} from "@/components/data-display";
import { getHomeData } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home({ searchParams }: { searchParams: Promise<{ search?: string }> }) {
  const params = await searchParams;
  const query = typeof params.search === "string" ? params.search : "";
  const data = await getHomeData(query);

  return (
    <main className="page-enter">
      <div className="mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
        <section className="grid gap-8 border-2 border-foreground bg-surface-berry p-6 shadow-[4px_4px_0_var(--section-ink)] sm:p-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end lg:p-10">
          <div>
            <h1 className="max-w-2xl font-heading text-4xl font-bold leading-[1.04] tracking-tight text-surface-berry-foreground sm:text-[44px]">
              Explore K-pop music show wins.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-surface-berry-foreground/80 sm:text-lg">
              Search artists, compare songs, and browse winners from six weekly
              shows since 2014.
            </p>
          </div>
          <div className="border-l-4 border-highlight-yellow bg-section-ink px-5 py-4 text-surface-berry-foreground">
            <p className="font-heading text-3xl font-bold tabular-nums">
              2014–today
            </p>
            <p className="mt-1 text-sm leading-relaxed text-surface-berry-foreground/75">
              Six weekly music shows in one searchable archive.
            </p>
          </div>
        </section>

        <div className="mt-8">
          <ArtistSearch query={query} results={data.artistResults} resultCount={data.artistResultCount} />
        </div>
        <ErrorState messages={data.errors} />

        <section id="wins" className="mt-14">
          <SectionHeading title="Recent wins" />
          <RecentWins wins={data.wins} />
        </section>

        <div className="mt-14 grid gap-12 lg:grid-cols-2">
          <section id="artists">
            <SectionHeading title="Artist leaderboard" />
            <Leaderboard
              rows={data.artists}
              kind="artist"
              empty="No artist rankings are available right now."
            />
          </section>
          <section id="songs">
            <SectionHeading title="Song leaderboard" />
            <Leaderboard
              rows={data.songs}
              kind="song"
              empty="No song rankings are available right now."
            />
          </section>
        </div>

        <section id="shows" className="mt-14">
          <SectionHeading title="Music shows" />
          <p className="mb-5 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            The archive covers six weekly Korean music shows, with historical
            results beginning in 2014.
          </p>
          <MusicShowList shows={data.shows} />
        </section>
      </div>
    </main>
  );
}
