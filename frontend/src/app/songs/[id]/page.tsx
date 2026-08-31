import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArtistWinHistory } from "@/components/artist-win-history";
import { EmptyState, ShowBadge, formatDate } from "@/components/data-display";
import { ApiRequestError, getAllSongWins, getSong } from "@/lib/api";
import { buildShowBreakdown, summarizeArtist } from "@/lib/artist-profile";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const dynamic = "force-dynamic";

function songId(value: string) {
  return /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null;
}

async function loadSong(id: number) {
  try { return await getSong(id); }
  catch (error) { if (error instanceof ApiRequestError && error.status === 404) notFound(); throw error; }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const id = songId((await params).id);
  if (!id) return { title: "Song not found", description: "The requested song could not be found in KpopWins." };
  try {
    const song = await getSong(id);
    return { title: `${song.title} by ${song.artist.name}`, description: `See every recorded music show win for ${song.title} by ${song.artist.name}.` };
  } catch { return { title: "Song not found", description: "The requested song could not be found in KpopWins." }; }
}

export default async function SongPage({ params }: { params: Promise<{ id: string }> }) {
  const id = songId((await params).id);
  if (!id) notFound();
  const song = await loadSong(id);
  const wins = await getAllSongWins(id);
  const summary = summarizeArtist(wins);
  const shows = buildShowBreakdown(wins);

  return <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
    <header className="grid gap-6 border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8 lg:grid-cols-[1fr_auto] lg:items-end"><div><h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">{song.title}</h1><p className="mt-2 text-surface-berry-foreground/75">by <Link href={`/artists/${song.artist.id}`} className="font-semibold underline-offset-4 hover:underline">{song.artist.name}</Link></p></div><div className="border-l-4 border-highlight-yellow bg-section-ink px-6 py-4"><p className="font-heading text-4xl font-bold tabular-nums">{song.total_wins}</p><p className="text-sm text-surface-berry-foreground/75">total {song.total_wins === 1 ? "win" : "wins"}</p></div></header>
    <section className="mt-10" aria-labelledby="summary-title"><h2 id="summary-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Summary</h2><dl className="grid border border-border bg-card sm:grid-cols-2 lg:grid-cols-4"><Metric label="Total wins" value={String(song.total_wins)} /><Metric label="Shows with wins" value={String(song.winning_shows)} /><Metric label="First win" value={summary.firstWin ? formatDate(summary.firstWin) : "Not recorded"} /><Metric label="Latest win" value={song.latest_win_date ? formatDate(song.latest_win_date) : "Not recorded"} /></dl></section>
    <section className="mt-12" aria-labelledby="shows-title"><h2 id="shows-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Wins by show</h2>{shows.length ? <div className="border border-border bg-card"><Table className="desktop-table border-collapse"><TableCaption className="sr-only">Song wins by music show</TableCaption><TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="px-4 py-3">Show</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader><TableBody>{shows.map((show) => <TableRow key={show.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-3"><ShowBadge slug={show.slug} name={show.name} /></TableCell><TableCell className="px-4 py-3 text-right font-heading text-lg font-bold tabular-nums">{show.wins}</TableCell></TableRow>)}</TableBody></Table><ul className="mobile-record flex-col">{shows.map((show) => <li key={show.id} className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0"><ShowBadge slug={show.slug} name={show.name} /><strong className="font-heading text-lg tabular-nums">{show.wins}</strong></li>)}</ul></div> : <EmptyState message="No music show wins are recorded for this song." />}</section>
    <section className="mt-12" aria-labelledby="history-title"><div className="mb-4 flex items-end justify-between gap-4 border-b-2 border-foreground pb-3"><h2 id="history-title" className="font-heading text-2xl font-bold">Win history</h2><span className="text-sm text-muted-foreground">Newest first</span></div><ArtistWinHistory wins={wins} emptyMessage="No wins with dates are recorded for this song." hideSong /></section>
  </main>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-border p-4 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 font-heading text-2xl font-bold tabular-nums">{value}</dd></div>;
}
