import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { Song } from "@/lib/api-shared";
import { EmptyState, formatDate } from "@/components/data-display";

function SongFacts({ song }: { song: Song }) {
  return <>
    <span className="text-sm tabular-nums"><strong>{song.total_wins}</strong> {song.total_wins === 1 ? "win" : "wins"}</span>
    <span className="text-sm tabular-nums text-muted-foreground">{song.latest_win_date ? `Latest ${formatDate(song.latest_win_date)}` : "No dated wins"}</span>
    <span className="text-sm tabular-nums text-muted-foreground"><strong className="text-foreground">{song.winning_shows}</strong> {song.winning_shows === 1 ? "show" : "shows"}</span>
  </>;
}

export function SongResults({ songs, empty }: { songs: Song[]; empty: string }) {
  if (!songs.length) return <EmptyState message={empty} />;
  return (
    <div className="border-2 border-foreground bg-card">
      <div className="hidden grid-cols-[minmax(13rem,1fr)_minmax(10rem,0.8fr)_6rem_9rem_5rem_1.25rem] gap-4 border-b-2 border-foreground bg-muted/50 px-4 py-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground lg:grid"><span>Song</span><span>Artist</span><span className="text-right">Wins</span><span>Latest win</span><span className="text-right">Shows</span><span /></div>
      {songs.map((song) => <Link key={song.id} href={`/songs/${song.id}`} className="group relative grid gap-2 border-b border-border px-4 py-4 pr-12 transition-colors hover:bg-accent focus-visible:bg-accent lg:grid-cols-[minmax(13rem,1fr)_minmax(10rem,0.8fr)_6rem_9rem_5rem_1.25rem] lg:items-center lg:gap-4 lg:pr-4 lg:last:border-b-0">
        <div><p className="font-heading text-lg font-bold">{song.title}</p><p className="text-sm text-muted-foreground lg:hidden">{song.artist.name}</p></div>
        <p className="hidden text-sm lg:block">{song.artist.name}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 lg:contents"><SongFacts song={song} /></div>
        <ArrowRight className="absolute right-4 top-5 size-4 text-brand-pink transition-transform group-hover:translate-x-1 lg:static lg:justify-self-end" aria-hidden="true" />
      </Link>)}
    </div>
  );
}
