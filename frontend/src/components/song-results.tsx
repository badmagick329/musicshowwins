import Link from "next/link";
import type { Song } from "@/lib/api-shared";
import { EmptyState } from "@/components/data-display";
import { formatDate } from "@/lib/utils";
import { artistPath } from "@/lib/paths";

// Each song is rendered once: a card on phones, a table-like row from `md` up. Unit words
// are visible on cards and screen-reader-only in rows, where the column header names them.
const columns = "grid grid-cols-[auto_minmax(0,1fr)_auto] items-baseline gap-x-3 gap-y-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_5rem_9rem_5rem] md:gap-x-6";

export function SongResults({ songs, empty }: { songs: Song[]; empty: string }) {
  if (!songs.length) return <EmptyState message={empty} />;
  return (
    <div className="border-2 bg-card">
      <div aria-hidden="true" className={`${columns} hidden border-b-2 bg-muted/50 px-4 py-3 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground md:grid`}>
        <span>Song</span><span>Artist</span><span className="text-right">Wins</span><span>Latest win</span><span className="text-right">Shows</span>
      </div>
      <ul aria-label="Song search results">
        {songs.map((song) => <li key={song.id} className={`${columns} border-b border-border/70 px-4 py-4 last:border-b-0 md:hover:bg-accent/60`}>
          <Link prefetch={false} href={`/songs/${song.id}`} className="compact-link-target col-span-3 min-w-0 break-words font-heading text-lg font-bold md:col-span-1">{song.title}</Link>
          <Link prefetch={false} href={artistPath(song.artist)} className="compact-link-target col-span-3 -mt-2 min-w-0 break-words text-sm text-muted-foreground md:col-span-1 md:mt-0 md:text-base md:text-foreground">{song.artist.name}</Link>
          <span className="whitespace-nowrap text-sm tabular-nums md:text-right md:text-base"><strong>{song.total_wins}</strong><span className="md:sr-only"> {song.total_wins === 1 ? "win" : "wins"}</span></span>
          <span className="min-w-0 text-center text-sm tabular-nums text-muted-foreground md:text-left md:text-base">{song.latest_win_date ? <><span className="md:sr-only">Latest win </span>{formatDate(song.latest_win_date)}</> : "No win date recorded"}</span>
          <span className="whitespace-nowrap text-right text-sm tabular-nums text-muted-foreground md:text-base md:text-foreground"><strong className="text-foreground md:font-normal">{song.winning_shows}</strong><span className="md:sr-only"> {song.winning_shows === 1 ? "show" : "shows"}</span></span>
        </li>)}
      </ul>
    </div>
  );
}
