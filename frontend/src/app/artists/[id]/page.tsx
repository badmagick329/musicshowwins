import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EmptyState, ShowBadge } from "@/components/data-display";
import { formatDate } from "@/lib/utils";
import { ApiRequestError, getAllArtistSongs, getAllArtistWins, getArtist } from "@/lib/api";
import { buildShowBreakdown, summarizeArtist } from "@/lib/artist-profile";
import { ArtistWinHistory } from "@/components/artist-win-history";
import { WinMoments } from "@/components/win-moments";
import { JsonLd } from "@/components/json-ld";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
  } catch { return { title: "Artist not found", description: "The requested artist could not be found in KpopWins.", robots: noIndexFollow }; }
}

export default async function ArtistPage({ params }: { params: Promise<{ id: string }> }) {
  const id = artistId((await params).id);
  if (!id) notFound();
  const artist = await loadArtist(id);
  const [songs, wins] = await Promise.all([getAllArtistSongs(id), getAllArtistWins(id)]);
  const summary = summarizeArtist(wins);
  const shows = buildShowBreakdown(wins);

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
        <h2 id="summary-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Summary</h2>
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

      <WinMoments wins={wins} />

      <div className="mt-12 grid gap-12 lg:grid-cols-[0.75fr_1.25fr]">
        <section aria-labelledby="shows-title">
          <h2 id="shows-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Wins by show</h2>
          {shows.length ? <div className="border border-border bg-card"><Table className="desktop-table border-collapse"><TableCaption className="sr-only">Artist wins by music show</TableCaption><TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="px-4 py-3">Show</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader><TableBody>{shows.map((show) => <TableRow key={show.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-3"><ShowBadge slug={show.slug} name={show.name} /></TableCell><TableCell className="px-4 py-3 text-right font-heading text-lg font-bold tabular-nums">{show.wins}</TableCell></TableRow>)}</TableBody></Table><ul className="mobile-record flex-col">{shows.map((show) => <li key={show.id} className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0"><ShowBadge slug={show.slug} name={show.name} /><strong className="font-heading text-lg tabular-nums">{show.wins}</strong></li>)}</ul></div> : <EmptyState message="No music show wins are recorded for this artist." />}
        </section>
        <section aria-labelledby="songs-title">
          <h2 id="songs-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Songs</h2>
          {songs.length ? <div className="border border-border bg-card"><Table className="desktop-table border-collapse"><TableCaption className="sr-only">Artist winning songs ranked by wins</TableCaption><TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-20 px-4 py-3">Rank</TableHead><TableHead className="px-4 py-3">Song</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader><TableBody>{songs.map((song, index) => <TableRow key={song.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-3 font-heading font-bold tabular-nums text-muted-foreground">{index + 1}</TableCell><TableCell className="px-4 py-3"><Link prefetch={false} href={`/songs/${song.id}`} className="compact-link-target font-semibold">{song.title}</Link></TableCell><TableCell className="px-4 py-3 text-right font-bold tabular-nums">{song.total_wins}</TableCell></TableRow>)}</TableBody></Table><ol className="mobile-record flex-col">{songs.map((song, index) => <li key={song.id} className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0"><span className="font-heading font-bold tabular-nums text-muted-foreground">{index + 1}</span><Link prefetch={false} href={`/songs/${song.id}`} className="compact-link-target font-semibold">{song.title}</Link><span className="tabular-nums"><strong>{song.total_wins}</strong> {song.total_wins === 1 ? "win" : "wins"}</span></li>)}</ol></div> : <EmptyState message="No songs are recorded for this artist." />}
        </section>
      </div>

      <section className="mt-12" aria-labelledby="history-title">
        <div className="mb-4 flex items-end justify-between gap-4 border-b-2 border-foreground pb-3"><h2 id="history-title" className="font-heading text-2xl font-bold">Win history</h2><span className="text-sm text-muted-foreground">Newest first</span></div>
        <ArtistWinHistory wins={wins} />
      </section>
    </main>
    </>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="min-w-0 border-b border-border p-4 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-heading text-2xl font-bold tabular-nums">{value}</dd></div>;
}
