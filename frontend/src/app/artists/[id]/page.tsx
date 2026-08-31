import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EmptyState, ShowBadge, formatDate } from "@/components/data-display";
import { ApiRequestError, getAllArtistSongs, getAllArtistWins, getArtist } from "@/lib/api";
import { buildShowBreakdown, summarizeArtist } from "@/lib/artist-profile";
import { ArtistWinHistory } from "@/components/artist-win-history";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const dynamic = "force-dynamic";

function artistId(value: string) {
  return /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null;
}

async function loadArtist(id: number) {
  try { return await getArtist(id); }
  catch (error) { if (error instanceof ApiRequestError && error.status === 404) notFound(); throw error; }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const id = artistId((await params).id);
  if (!id) return { title: "Artist not found", description: "The requested artist could not be found in KpopWins." };
  try {
    const artist = await getArtist(id);
    return { title: `${artist.name} Music Show Wins`, description: `See ${artist.name}'s winning songs and complete music show win history.` };
  } catch { return { title: "Artist not found", description: "The requested artist could not be found in KpopWins." }; }
}

export default async function ArtistPage({ params }: { params: Promise<{ id: string }> }) {
  const id = artistId((await params).id);
  if (!id) notFound();
  const artist = await loadArtist(id);
  const [songs, wins] = await Promise.all([getAllArtistSongs(id), getAllArtistWins(id)]);
  const summary = summarizeArtist(wins);
  const shows = buildShowBreakdown(wins);

  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="grid gap-6 border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div><h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">{artist.name}</h1><p className="mt-2 text-surface-berry-foreground/75">Music show wins</p></div>
        <div className="border-l-4 border-highlight-yellow bg-section-ink px-6 py-4"><p className="font-heading text-4xl font-bold tabular-nums">{artist.total_wins}</p><p className="text-sm text-surface-berry-foreground/75">total {artist.total_wins === 1 ? "win" : "wins"}</p></div>
      </header>

      <section className="mt-10" aria-labelledby="summary-title">
        <h2 id="summary-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Summary</h2>
        <dl className="grid border border-border bg-card sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Total wins" value={String(summary.totalWins)} />
          <Metric label="Winning songs" value={String(summary.winningSongs)} />
          <Metric label="First win" value={summary.firstWin ? formatDate(summary.firstWin) : "Not recorded"} />
          <Metric label="Latest win" value={summary.latestWin ? formatDate(summary.latestWin) : "Not recorded"} />
        </dl>
      </section>

      <div className="mt-12 grid gap-12 lg:grid-cols-[0.75fr_1.25fr]">
        <section aria-labelledby="shows-title">
          <h2 id="shows-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Wins by show</h2>
          {shows.length ? <div className="border border-border bg-card"><Table className="desktop-table border-collapse"><TableCaption className="sr-only">Artist wins by music show</TableCaption><TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="px-4 py-3">Show</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader><TableBody>{shows.map((show) => <TableRow key={show.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-3"><ShowBadge slug={show.slug} name={show.name} /></TableCell><TableCell className="px-4 py-3 text-right font-heading text-lg font-bold tabular-nums">{show.wins}</TableCell></TableRow>)}</TableBody></Table><ul className="mobile-record flex-col">{shows.map((show) => <li key={show.id} className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0"><ShowBadge slug={show.slug} name={show.name} /><strong className="font-heading text-lg tabular-nums">{show.wins}</strong></li>)}</ul></div> : <EmptyState message="No music show wins are recorded for this artist." />}
        </section>
        <section aria-labelledby="songs-title">
          <h2 id="songs-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Songs</h2>
          {songs.length ? <div className="border border-border bg-card"><Table className="desktop-table border-collapse"><TableCaption className="sr-only">Artist winning songs ranked by wins</TableCaption><TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-20 px-4 py-3">Rank</TableHead><TableHead className="px-4 py-3">Song</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader><TableBody>{songs.map((song, index) => <TableRow key={song.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-3 font-heading font-bold tabular-nums text-muted-foreground">{index + 1}</TableCell><TableCell className="px-4 py-3"><Link href={`/songs/${song.id}`} className="font-semibold underline-offset-4 hover:underline">{song.title}</Link></TableCell><TableCell className="px-4 py-3 text-right font-bold tabular-nums">{song.total_wins}</TableCell></TableRow>)}</TableBody></Table><ol className="mobile-record flex-col">{songs.map((song, index) => <li key={song.id} className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0"><span className="font-heading font-bold tabular-nums text-muted-foreground">{index + 1}</span><Link href={`/songs/${song.id}`} className="font-semibold underline-offset-4 hover:underline">{song.title}</Link><span className="tabular-nums"><strong>{song.total_wins}</strong> {song.total_wins === 1 ? "win" : "wins"}</span></li>)}</ol></div> : <EmptyState message="No songs are recorded for this artist." />}
        </section>
      </div>

      <section className="mt-12" aria-labelledby="history-title">
        <div className="mb-4 flex items-end justify-between gap-4 border-b-2 border-foreground pb-3"><h2 id="history-title" className="font-heading text-2xl font-bold">Win history</h2><span className="text-sm text-muted-foreground">Newest first</span></div>
        <ArtistWinHistory wins={wins} />
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-border p-4 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 font-heading text-2xl font-bold tabular-nums">{value}</dd></div>;
}
