import Link from "next/link";
import type { Artist } from "@/lib/api-shared";
import { EmptyState } from "@/components/data-display";
import { formatDate } from "@/lib/utils";
import { artistPath } from "@/lib/paths";

// Each artist is rendered once: a stacked card on phones, a table-like row from `md` up.
// Unit words are visible on cards and screen-reader-only in rows, where the column header names them.
const columns = "grid gap-2 md:grid-cols-[minmax(0,1fr)_6rem_9rem_9rem] md:items-baseline md:gap-x-6";

export function ArtistResults({ artists, empty }: { artists: Artist[]; empty: string }) {
  if (!artists.length) return <EmptyState message={empty} />;
  return (
    <div className="border-2 bg-card">
      <div aria-hidden="true" className={`${columns} hidden border-b-2 bg-muted/50 px-4 py-3 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground md:grid`}>
        <span>Artist</span><span className="text-right">Wins</span><span className="text-right">Winning songs</span><span>Latest win</span>
      </div>
      <ul aria-label="Artist search results" className="divide-y divide-border">
        {artists.map((artist) => <li key={artist.id} className={`${columns} relative px-4 py-4 transition-colors hover:bg-accent/60`}>
          <Link prefetch={false} href={artistPath(artist)} className="min-w-0 break-words font-heading text-lg font-bold underline-offset-4 after:absolute after:inset-0 hover:underline focus-visible:after:outline-2 focus-visible:after:outline-offset-[-2px] focus-visible:after:outline-brand-pink">{artist.name}</Link>
          <span className="text-sm tabular-nums md:text-right md:text-base"><strong>{artist.total_wins}</strong><span className="md:sr-only"> {artist.total_wins === 1 ? "win" : "wins"}</span></span>
          <span className="text-sm tabular-nums text-muted-foreground md:text-right md:text-base md:text-foreground"><strong className="text-foreground md:font-normal">{artist.winning_songs}</strong><span className="md:sr-only"> winning {artist.winning_songs === 1 ? "song" : "songs"}</span></span>
          <span className="text-sm tabular-nums text-muted-foreground md:text-base">{artist.latest_win_date ? <><span className="md:sr-only">Latest win </span>{formatDate(artist.latest_win_date)}</> : "No win date recorded"}</span>
        </li>)}
      </ul>
    </div>
  );
}
