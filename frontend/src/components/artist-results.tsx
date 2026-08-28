import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { Artist } from "@/lib/api";
import { EmptyState, formatDate } from "@/components/data-display";

export function ArtistResults({ artists, empty }: { artists: Artist[]; empty: string }) {
  if (!artists.length) return <EmptyState message={empty} />;
  return (
    <ul className="divide-y divide-border border-2 border-foreground bg-card">
      {artists.map((artist) => (
        <li key={artist.id}>
          <Link
            href={`/artists/${artist.id}`}
            className="group grid gap-2 px-4 py-4 transition-colors hover:bg-accent focus-visible:bg-accent sm:grid-cols-[minmax(10rem,1fr)_8rem_10rem_9rem] sm:items-center"
          >
            <span className="font-heading text-lg font-bold">{artist.name}</span>
            <span className="text-sm tabular-nums"><strong>{artist.total_wins}</strong> {artist.total_wins === 1 ? "win" : "wins"}</span>
            <span className="text-sm tabular-nums text-muted-foreground"><strong className="text-foreground">{artist.winning_songs}</strong> winning {artist.winning_songs === 1 ? "song" : "songs"}</span>
            <span className="flex items-center justify-between gap-3 text-sm text-muted-foreground sm:justify-end">
              <span>{artist.latest_win_date ? `Latest ${formatDate(artist.latest_win_date)}` : "No dated wins"}</span>
              <ArrowRight className="size-4 shrink-0 text-brand-pink transition-transform group-hover:translate-x-1" aria-label="View history" />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
