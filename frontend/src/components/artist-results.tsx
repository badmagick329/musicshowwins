import Link from "next/link";
import type { Artist } from "@/lib/api-shared";
import { EmptyState, formatDate } from "@/components/data-display";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function ArtistResults({ artists, empty }: { artists: Artist[]; empty: string }) {
  if (!artists.length) return <EmptyState message={empty} />;
  return (
    <div className="border-2 border-foreground bg-card">
      <Table className="desktop-table border-collapse">
        <TableCaption className="sr-only">Artist search results</TableCaption>
        <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="px-4 py-3">Artist</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead><TableHead className="w-36 px-4 py-3 text-right">Winning songs</TableHead><TableHead className="w-36 px-4 py-3">Latest win</TableHead></TableRow></TableHeader>
        <TableBody>{artists.map((artist) => <TableRow key={artist.id} className="relative cursor-pointer border-border/70 hover:bg-accent/60"><TableCell className="px-4 py-4"><Link href={`/artists/${artist.id}`} className="font-heading text-lg font-bold underline-offset-4 after:absolute after:inset-0 hover:underline focus-visible:after:outline-2 focus-visible:after:outline-offset-[-2px] focus-visible:after:outline-brand-pink">{artist.name}</Link></TableCell><TableCell className="px-4 py-4 text-right font-bold tabular-nums">{artist.total_wins}</TableCell><TableCell className="px-4 py-4 text-right tabular-nums">{artist.winning_songs}</TableCell><TableCell className="px-4 py-4 tabular-nums text-muted-foreground">{artist.latest_win_date ? formatDate(artist.latest_win_date) : "No dated wins"}</TableCell></TableRow>)}</TableBody>
      </Table>
      <ul className="mobile-record flex-col divide-y divide-border">
        {artists.map((artist) => <li key={artist.id}>
          <Link
            href={`/artists/${artist.id}`}
            className="group grid gap-2 px-4 py-4 transition-colors hover:bg-accent focus-visible:bg-accent"
          >
            <span className="font-heading text-lg font-bold">{artist.name}</span>
            <span className="text-sm tabular-nums"><strong>{artist.total_wins}</strong> {artist.total_wins === 1 ? "win" : "wins"}</span>
            <span className="text-sm tabular-nums text-muted-foreground"><strong className="text-foreground">{artist.winning_songs}</strong> winning {artist.winning_songs === 1 ? "song" : "songs"}</span>
            <span className="text-sm text-muted-foreground">{artist.latest_win_date ? `Latest ${formatDate(artist.latest_win_date)}` : "No dated wins"}</span>
          </Link>
        </li>)}
      </ul>
    </div>
  );
}
