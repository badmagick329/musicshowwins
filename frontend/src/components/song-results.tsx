import Link from "next/link";
import type { Song } from "@/lib/api-shared";
import { EmptyState } from "@/components/data-display";
import { formatDate } from "@/lib/utils";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function SongFacts({ song }: { song: Song }) {
  return <>
    <span className="text-sm tabular-nums"><strong>{song.total_wins}</strong> {song.total_wins === 1 ? "win" : "wins"}</span>
    <span className="text-sm tabular-nums text-muted-foreground">{song.latest_win_date ? `Latest win ${formatDate(song.latest_win_date)}` : "No win date recorded"}</span>
    <span className="text-sm tabular-nums text-muted-foreground"><strong className="text-foreground">{song.winning_shows}</strong> {song.winning_shows === 1 ? "show" : "shows"}</span>
  </>;
}

export function SongResults({ songs, empty }: { songs: Song[]; empty: string }) {
  if (!songs.length) return <EmptyState message={empty} />;
  return (
    <div className="border-2 border-foreground bg-card">
      <Table className="desktop-table border-collapse">
        <TableCaption className="sr-only">Song search results</TableCaption>
        <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="px-4 py-3">Song</TableHead><TableHead className="px-4 py-3">Artist</TableHead><TableHead className="w-20 px-4 py-3 text-right">Wins</TableHead><TableHead className="w-36 px-4 py-3">Latest win</TableHead><TableHead className="w-20 px-4 py-3 text-right">Shows</TableHead></TableRow></TableHeader>
        <TableBody>{songs.map((song) => <TableRow key={song.id} className="border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-4"><Link prefetch={false} href={`/songs/${song.id}`} className="font-heading text-lg font-bold underline-offset-4 hover:underline">{song.title}</Link></TableCell><TableCell className="px-4 py-4"><Link prefetch={false} href={`/artists/${song.artist.id}`} className="underline-offset-4 hover:underline">{song.artist.name}</Link></TableCell><TableCell className="px-4 py-4 text-right font-bold tabular-nums">{song.total_wins}</TableCell><TableCell className="px-4 py-4 tabular-nums text-muted-foreground">{song.latest_win_date ? formatDate(song.latest_win_date) : "No win date recorded"}</TableCell><TableCell className="px-4 py-4 text-right tabular-nums">{song.winning_shows}</TableCell></TableRow>)}</TableBody>
      </Table>
      <div className="mobile-record flex-col">
      {songs.map((song) => <Link prefetch={false} key={song.id} href={`/songs/${song.id}`} className="group grid gap-2 border-b border-border px-4 py-4 transition-colors last:border-b-0 hover:bg-accent focus-visible:bg-accent">
        <div><p className="font-heading text-lg font-bold">{song.title}</p><p className="text-sm text-muted-foreground lg:hidden">{song.artist.name}</p></div>
        <div className="flex flex-wrap gap-x-4 gap-y-1"><SongFacts song={song} /></div>
      </Link>)}
      </div>
    </div>
  );
}
