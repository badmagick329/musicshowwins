import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArtistWinsByYear } from "@/components/artist-wins-by-year";
import { parseArtistYear } from "@/lib/artist-years";
import { formatDate } from "@/lib/utils";
import { ApiRequestError, getAllArtistWins, getArtist } from "@/lib/api";
import { summarizeArtist } from "@/lib/artist-profile";
import { JsonLd } from "@/components/json-ld";
import { noIndexFollow, pageMetadata, siteUrl } from "@/lib/seo";

function artistId(value: string) {
  return /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null;
}

async function loadArtist(id: number) {
  try { return await getArtist(id); }
  catch (error) { if (error instanceof ApiRequestError && error.status === 404) notFound(); throw error; }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const id = artistId((await params).id);
  if (!id) return { title: "Artist not found", description: "The requested artist could not be found in KpopWins.", robots: noIndexFollow };
  try {
    const artist = await getArtist(id);
    return pageMetadata({
      title: `${artist.name} Music Show Wins`,
      description: `Explore ${artist.name}'s ${artist.total_wins} recorded music-show ${artist.total_wins === 1 ? "win" : "wins"} across ${artist.winning_songs} ${artist.winning_songs === 1 ? "song" : "songs"}, with totals by song and show and a dated win history.`,
      path: `/artists/${id}`,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return { title: "Artist not found", description: "The requested artist could not be found in KpopWins.", robots: noIndexFollow };
    throw error;
  }
}

export default async function ArtistPage({ params, searchParams = Promise.resolve({}) }: { params: Promise<{ id: string }>; searchParams?: Promise<{ year?: string | string[] }> }) {
  const id = artistId((await params).id);
  if (!id) notFound();
  const artist = await loadArtist(id);
  const wins = await getAllArtistWins(id);
  const summary = summarizeArtist(wins);

  return (
    <>
      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: siteUrl },
          { "@type": "ListItem", position: 2, name: "Artists", item: `${siteUrl}/artists` },
          { "@type": "ListItem", position: 3, name: artist.name, item: `${siteUrl}/artists/${id}` },
        ],
      }} />
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">{artist.name}</h1><p className="mt-2 text-surface-berry-foreground/75">Music show wins</p>
      </header>

      <section className="mt-10" aria-labelledby="summary-title">
        <h2 id="summary-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Career summary</h2>
        <dl className="grid border border-border bg-card sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Total wins" value={String(summary.totalWins)} />
          <Metric label="Winning songs" value={String(summary.winningSongs)} />
          <Metric label="Earliest recorded win" value={summary.earliestWin ? <>
            <Link prefetch={false} href={`/songs/${summary.earliestWin.song.id}`} className="compact-link-target text-lg leading-snug underline underline-offset-4">{summary.earliestWin.song.title}</Link>
            <span className="mt-1 block font-sans text-sm font-normal leading-relaxed">
              {summary.earliestWin.show.name}<br />
              <time dateTime={summary.earliestWin.date}>{formatDate(summary.earliestWin.date)}</time>
            </span>
          </> : "Not recorded"} />
          <Metric label="Latest win" value={summary.latestWin ? formatDate(summary.latestWin) : "Not recorded"} />
        </dl>
      </section>

      <ArtistWinsByYear artist={artist} wins={wins} initialYear={parseArtistYear((await searchParams).year)} />
    </main>
    </>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="min-w-0 border-b border-border p-4 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-heading text-2xl font-bold tabular-nums">{value}</dd></div>;
}
