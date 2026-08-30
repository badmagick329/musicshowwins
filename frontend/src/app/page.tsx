import { ArtistSearch } from "@/components/artist-search";
import Link from "next/link";
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
        <section className="border-2 border-foreground bg-surface-berry p-6 shadow-[4px_4px_0_var(--section-ink)] sm:p-8 lg:p-10">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl font-bold leading-[1.04] tracking-tight text-surface-berry-foreground sm:text-[44px]">Explore K-pop music show wins.</h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-surface-berry-foreground/80 sm:text-lg">Search artists, songs, and weekly music-show winners from 2014 onward.</p>
          </div>
        </section>

        <div className="mt-8">
          <ArtistSearch query={query} results={data.artistResults} resultCount={data.artistResultCount} />
        </div>
        <ErrorState messages={data.errors} />

        <section id="wins" className="mt-14">
          <SectionHeading title="Recent wins" action={<Link href="/wins" className="text-sm font-bold text-brand-pink underline-offset-4 hover:underline">Browse all wins</Link>} />
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
            <SectionHeading title="Song leaderboard" action={<Link href="/songs" className="text-sm font-bold text-brand-pink underline-offset-4 hover:underline">Browse all songs</Link>} />
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
