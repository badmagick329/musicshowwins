import { ArtistSearch } from "@/components/artist-search";
import { TopWinsThisYearLink } from "@/components/top-wins-this-year-link";
import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import {
  ErrorState,
  Leaderboard,
  MusicShowList,
  SectionHeading,
} from "@/components/data-display";
import { getHomeData } from "@/lib/api";
import { archiveToday } from "@/lib/rankings";
import { koreaToday } from "@/lib/this-week";
import { ThisWeek } from "@/components/this-week";
import { noIndexFollow, siteDescription, siteName, siteUrl } from "@/lib/seo";

export async function generateMetadata({ searchParams }: { searchParams: Promise<{ search?: string | string[]; rankings?: string | string[] }> }): Promise<Metadata> {
  const { search, rankings } = await searchParams;
  const hasSearch = typeof search === "string" && Boolean(search.trim());
  if (!hasSearch && rankings !== "all-time") return { alternates: { canonical: "/" } };
  return {
    ...(hasSearch ? { title: "Artist Search Results", description: siteDescription } : {}),
    alternates: { canonical: "/" },
    robots: noIndexFollow,
  };
}

export default async function Home({ searchParams }: { searchParams: Promise<{ search?: string; rankings?: string }> }) {
  const params = await searchParams;
  const query = typeof params.search === "string" ? params.search : "";
  const period = params.rankings === "all-time" ? "all-time" : "year";
  const today = archiveToday();
  const year = today.slice(0, 4);
  const searchParam = query.trim() ? `search=${encodeURIComponent(query.trim())}` : "";
  const thisYearHref = searchParam ? `/?${searchParam}` : "/";
  const allTimeHref = `/?${searchParam ? `${searchParam}&` : ""}rankings=all-time`;
  const koreaDate = koreaToday();
  const data = await getHomeData(query, period, today, koreaDate);

  return (
    <>
      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "Dataset",
        name: "KpopWins music show wins archive",
        description: siteDescription,
        url: siteUrl,
        creator: { "@type": "Organization", name: siteName, url: siteUrl },
        license: "https://creativecommons.org/licenses/by-sa/4.0/",
        isAccessibleForFree: true,
        temporalCoverage: "2014-01-01/..",
        keywords: ["K-pop", "music show wins", "artists", "songs", "Korean music shows"],
      }} />
    <main className="page-enter">
      <div className="mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
        {/* Kept short: the meta description carries the search copy, and on phones this block used to fill half the first screen. */}
        <section className="border-2 bg-surface-berry p-5 shadow-[4px_4px_0_var(--section-ink)] sm:p-6 lg:px-8">
          <h1 className="font-heading text-[28px] font-bold leading-tight tracking-tight text-surface-berry-foreground sm:text-[32px]">K-pop music show wins &amp; artist rankings</h1>
          <p className="mt-2 text-base text-surface-berry-foreground/80">Every music show win since 2014, by artist, song and show.</p>
          <TopWinsThisYearLink />
        </section>

        <div className="mt-8">
          <ArtistSearch query={query} results={data.artistResults} resultCount={data.artistResultCount} />
        </div>
        <ErrorState messages={data.errors} />

        <ThisWeek week={data.week} shows={data.shows} today={koreaDate} />

        <section className="mt-14" aria-labelledby="home-rankings-title">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b-2 pb-3">
            <h2 id="home-rankings-title" className="font-heading text-xl font-bold tracking-tight sm:text-2xl">Most wins {period === "year" ? `in ${year}` : "of all time"}</h2>
            <div role="group" aria-label="Leaderboard period" className="flex border-2 bg-card text-sm font-bold"><Link href={thisYearHref} aria-current={period === "year" ? "page" : undefined} className={`inline-flex min-h-11 items-center px-4 ${period === "year" ? "bg-action-pink text-white" : "hover:bg-accent"}`}>This year</Link><Link href={allTimeHref} aria-current={period === "all-time" ? "page" : undefined} className={`inline-flex min-h-11 items-center px-4 ${period === "all-time" ? "bg-action-pink text-white" : "hover:bg-accent"}`}>All time</Link></div>
          </div>
          <div className="grid gap-12 lg:grid-cols-2">
          <section id="artists">
            <SectionHeading level={3} title="Artists" action={<Link href={period === "year" ? "/rankings?kind=artists" : "/rankings?kind=artists&period=all-time"} className="compact-link-target text-sm font-bold text-link-pink">Full artist rankings →</Link>} />
            <Leaderboard
              rows={data.artists}
              kind="artist"
              empty="No artist rankings are available right now."
            />
          </section>
          <section id="songs">
            <SectionHeading level={3} title="Songs" action={<Link href={period === "year" ? "/rankings" : "/rankings?period=all-time"} className="compact-link-target text-sm font-bold text-link-pink">Full song rankings →</Link>} />
            <Leaderboard
              rows={data.songs}
              kind="song"
              empty="No song rankings are available right now."
            />
          </section>
          </div>
        </section>

        <section id="shows" className="mt-14">
          <SectionHeading title="Music shows" action={<Link href="/shows" className="compact-link-target text-sm font-bold text-link-pink">All shows</Link>} />
          <MusicShowList shows={data.shows} />
        </section>
      </div>
    </main>
    </>
  );
}
