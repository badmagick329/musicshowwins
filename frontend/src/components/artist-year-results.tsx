"use client";
import Link from "next/link";
import type { Win } from "@/lib/api-shared";
import { EmptyState, ShowWinsStrip } from "@/components/data-display";
import { buildShowBreakdown } from "@/lib/artist-profile";
import { ArtistWinHistory } from "@/components/artist-win-history";
import { WinMoments } from "@/components/win-moments";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function ArtistYearResults({ wins }: { wins: Win[] }) {
  const shows = buildShowBreakdown(wins);
  const counts = new Map<number, Win["song"]>();
  for (const win of wins) {
    const song = counts.get(win.song.id);
    if (song) song.total_wins += 1;
    else counts.set(win.song.id, { ...win.song, total_wins: 1 });
  }
  const songs = [...counts.values()].sort((a, b) => b.total_wins - a.total_wins || a.title.localeCompare(b.title));
  return <>
      <WinMoments wins={wins} />

      <section className="mt-12" aria-labelledby="shows-title">
        <h2 id="shows-title" className="mb-4 border-b-2 pb-3 font-heading text-2xl font-bold">Wins by show</h2>
        {shows.length ? <ShowWinsStrip shows={shows} label="Artist wins by music show" /> : <EmptyState message="No music show wins are recorded for this artist." />}
      </section>
      <section className="mt-12" aria-labelledby="songs-title">
        <h2 id="songs-title" className="mb-4 border-b-2 pb-3 font-heading text-2xl font-bold">Songs</h2>
        {/* Three narrow columns fit a phone, so one table serves every width rather than a hidden desktop table plus a mobile copy. */}
        {songs.length ? <div className="border border-border bg-card"><Table className="border-collapse"><TableCaption className="sr-only">Artist winning songs ranked by wins</TableCaption><TableHeader><TableRow className="border-b-2 bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-14 px-3 py-3 sm:w-20 sm:px-4">Rank</TableHead><TableHead className="px-3 py-3 sm:px-4">Song</TableHead><TableHead className="w-20 px-3 py-3 text-right sm:w-24 sm:px-4">Wins</TableHead></TableRow></TableHeader><TableBody>{songs.map((song, index) => <TableRow key={song.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-3 py-3 font-heading font-bold tabular-nums text-muted-foreground sm:px-4">{index + 1}</TableCell><TableCell className="whitespace-normal break-words px-3 py-3 sm:px-4"><Link prefetch={false} href={`/songs/${song.id}`} className="compact-link-target font-semibold">{song.title}</Link></TableCell><TableCell className="px-3 py-3 text-right font-bold tabular-nums sm:px-4">{song.total_wins}</TableCell></TableRow>)}</TableBody></Table></div> : <EmptyState message="No songs are recorded for this artist." />}
      </section>

      <section className="mt-12" aria-labelledby="history-title">
        <div className="mb-4 flex items-end justify-between gap-4 border-b-2 pb-3"><h2 id="history-title" className="font-heading text-2xl font-bold">Win history</h2><span className="text-sm text-muted-foreground">Newest first</span></div>
        <ArtistWinHistory wins={wins} />
      </section>
</>;
}
