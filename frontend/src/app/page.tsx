import { ArtistSearch } from "@/components/artist-search";
import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import {
  ErrorState,
  Leaderboard,
  MusicShowList,
  RecentWins,
  SectionHeading,
} from "@/components/data-display";
import { getHomeData } from "@/lib/api";
import { noIndexFollow, siteDescription, siteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({ searchParams }: { searchParams: Promise<{ search?: string | string[] }> }): Promise<Metadata> {
  const search = (await searchParams).search;
  if (typeof search !== "string" || !search.trim()) return { alternates: { canonical: "/" } };
  return {
    title: "Artist search results",
    description: siteDescription,
    alternates: { canonical: "/" },
    robots: noIndexFollow,
  };
}

export default async function Home({ searchParams }: { searchParams: Promise<{ search?: string }> }) {
  const params = await searchParams;
  const query = typeof params.search === "string" ? params.search : "";
  const data = await getHomeData(query);

  return (
    <>
      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "Dataset",
        name: "KpopWins music show wins archive",
        description: siteDescription,
        url: siteUrl,
        license: "https://creativecommons.org/licenses/by-sa/4.0/",
        isAccessibleForFree: true,
        temporalCoverage: "2014-01-01/..",
        keywords: ["K-pop", "music show wins", "artists", "songs", "Korean music shows"],
      }} />
    <main className="page-enter">
      <div className="mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
        <section className="border-2 border-foreground bg-surface-berry p-6 shadow-[4px_4px_0_var(--section-ink)] sm:p-8 lg:p-10">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl font-bold leading-[1.04] tracking-tight text-surface-berry-foreground sm:text-[44px]">K-pop music show wins since 2014.</h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-surface-berry-foreground/80 sm:text-lg">Search by artist or song and browse results from six weekly shows.</p>
          </div>
        </section>

        <div className="mt-8">
          <ArtistSearch query={query} results={data.artistResults} resultCount={data.artistResultCount} />
        </div>
        <ErrorState messages={data.errors} />

        <section id="wins" className="mt-14">
          <SectionHeading title="Recent wins" action={<Link href="/wins" className="text-sm font-bold text-brand-pink underline-offset-4 hover:underline">View all wins</Link>} />
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
            <SectionHeading title="Song leaderboard" action={<Link href="/songs" className="text-sm font-bold text-brand-pink underline-offset-4 hover:underline">All songs</Link>} />
            <Leaderboard
              rows={data.songs}
              kind="song"
              empty="No song rankings are available right now."
            />
          </section>
        </div>

        <section id="shows" className="mt-14">
          <SectionHeading title="Music shows" action={<Link href="/shows" className="text-sm font-bold text-brand-pink underline-offset-4 hover:underline">All shows</Link>} />
          <MusicShowList shows={data.shows} />
        </section>
      </div>
    </main>
    </>
  );
}
