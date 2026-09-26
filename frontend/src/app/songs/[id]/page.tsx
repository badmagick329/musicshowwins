import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArtistWinHistory } from "@/components/artist-win-history";
import { WinMoments } from "@/components/win-moments";
import { EmptyState, Metric, MetricGrid, ShowWinsStrip } from "@/components/data-display";
import { JsonLd } from "@/components/json-ld";
import { formatDate } from "@/lib/utils";
import { ApiRequestError, getAllSongWins, getSong } from "@/lib/api";
import { buildShowBreakdown, summarizeArtist } from "@/lib/artist-profile";
import { noIndexFollow, pageMetadata, plural, siteUrl } from "@/lib/seo";
import { artistPath } from "@/lib/paths";

function songId(value: string) {
  return /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null;
}

async function loadSong(id: number) {
  try { return await getSong(id); }
  catch (error) { if (error instanceof ApiRequestError && error.status === 404) notFound(); throw error; }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const id = songId((await params).id);
  if (!id) return { title: "Song Not Found", description: "The requested song could not be found in KpopWins.", robots: noIndexFollow };
  try {
    const [song, wins] = await Promise.all([getSong(id), getAllSongWins(id)]);
    const { earliestWin, latestWin } = summarizeArtist(wins);
    const counts = `${song.total_wins} recorded music-show ${plural(song.total_wins, "win")} across ${song.winning_shows} ${plural(song.winning_shows, "show")}`;
    const dates = earliestWin && latestWin
      ? ` Earliest recorded win: ${earliestWin.show.name}, ${formatDate(earliestWin.date)}.${latestWin.date === earliestWin.date ? "" : ` Latest: ${formatDate(latestWin.date)}.`}`
      : "";
    return pageMetadata({
      title: `${song.title} by ${song.artist.name}: ${song.total_wins} Music Show ${plural(song.total_wins, "Win")}`,
      description: `${song.title} by ${song.artist.name} has ${counts}.${dates}`,
      path: `/songs/${id}`,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return { title: "Song Not Found", description: "The requested song could not be found in KpopWins.", robots: noIndexFollow };
    throw error;
  }
}

export default async function SongPage({ params }: { params: Promise<{ id: string }> }) {
  const id = songId((await params).id);
  if (!id) notFound();
  const song = await loadSong(id);
  const wins = await getAllSongWins(id);
  const summary = summarizeArtist(wins);
  const shows = buildShowBreakdown(wins);

  return <>
    <JsonLd data={{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: siteUrl },
        { "@type": "ListItem", position: 2, name: "Songs", item: `${siteUrl}/songs` },
        { "@type": "ListItem", position: 3, name: song.title, item: `${siteUrl}/songs/${id}` },
      ],
    }} />
  <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
    <header className="border-2 bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8"><h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">{song.title}</h1><p className="mt-2 text-surface-berry-foreground/75">by <Link href={artistPath(song.artist)} className="font-semibold underline-offset-4 hover:underline">{song.artist.name}</Link></p></header>
    <section className="mt-10" aria-labelledby="summary-title"><h2 id="summary-title" className="mb-4 border-b-2 pb-3 font-heading text-2xl font-bold">Summary</h2><MetricGrid><Metric label="Total wins" value={String(song.total_wins)} /><Metric label="Shows with wins" value={String(song.winning_shows)} /><Metric label="First win" value={summary.earliestWin ? formatDate(summary.earliestWin.date) : "Not recorded"} /><Metric label="Latest win" value={song.latest_win_date ? formatDate(song.latest_win_date) : "Not recorded"} /></MetricGrid></section>
    <section className="mt-12" aria-labelledby="shows-title"><h2 id="shows-title" className="mb-4 border-b-2 pb-3 font-heading text-2xl font-bold">Wins by show</h2>{shows.length ? <ShowWinsStrip shows={shows} label="Song wins by music show" />: <EmptyState message="No music show wins are recorded for this song." />}</section>
    <WinMoments wins={wins} />
    <section className="mt-12" aria-labelledby="history-title"><div className="mb-4 flex items-end justify-between gap-4 border-b-2 pb-3"><h2 id="history-title" className="font-heading text-2xl font-bold">Win history</h2><span className="text-sm text-muted-foreground">Newest first</span></div><ArtistWinHistory wins={wins} emptyMessage="No wins with dates are recorded for this song." hideSong /></section>
  </main></>;
}
