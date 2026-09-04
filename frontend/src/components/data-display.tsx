import type {
  ArtistLeaderboardRow,
  Show,
  SongLeaderboardRow,
  Win,
} from "@/lib/api-shared";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DesktopWinVideoRow, MobileWinVideoDisclosure } from "@/components/win-videos";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import Link from "next/link";

export function SectionHeading({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4 border-b-2 border-foreground pb-3">
      <h2 className="font-heading text-xl font-bold tracking-tight sm:text-2xl">{title}</h2>
      {action}
    </div>
  );
}

const showLabels: Record<string, string> = {
  inkigayo: "Inkigayo",
  "m-countdown": "M Countdown",
  "music-bank": "Music Bank",
  "music-core": "Music Core",
  "show-champion": "Show Champion",
  "the-show": "The Show",
};

export function ShowBadge({ slug, name, className }: { slug: string; name?: string; className?: string }) {
  const showClass = `show-${slug}`;
  return (
    <span className={cn("show-badge inline-flex items-center border px-2 py-0.5 text-xs font-bold", showClass, className)}>
      {name ?? showLabels[slug] ?? slug}
    </span>
  );
}

export function RankMarker({ rank }: { rank: number }) {
  return <span className={cn("rank-marker", rank <= 3 && `rank-marker--${rank}`)}>{rank}</span>;
}

function leaderboardCopy(row: ArtistLeaderboardRow | SongLeaderboardRow, kind: "artist" | "song") {
  const artistRow = row as ArtistLeaderboardRow;
  const songRow = row as SongLeaderboardRow;
  const title = kind === "artist" ? artistRow.artist.name : songRow.song.title;
  const subtitle = kind === "song" ? songRow.song.artist.name : undefined;
  const artist = kind === "artist" ? artistRow.artist : songRow.song.artist;
  return { title, subtitle, artist, songId: kind === "song" ? songRow.song.id : undefined };
}

function DesktopLeaderboardRow({ row, kind }: { row: ArtistLeaderboardRow | SongLeaderboardRow; kind: "artist" | "song" }) {
  const { title, subtitle, artist, songId } = leaderboardCopy(row, kind);
  return (
    <TableRow className="border-border/70 transition-colors hover:bg-accent/60">
      <TableCell className="w-16 px-4 py-3"><RankMarker rank={row.rank} /></TableCell>
      <TableCell className="px-4 py-3"><p className="font-semibold">{kind === "artist" ? <Link prefetch={false} href={`/artists/${artist.id}`} className="underline-offset-4 hover:underline">{title}</Link> : <Link prefetch={false} href={`/songs/${songId}`} className="underline-offset-4 hover:underline">{title}</Link>}</p>{subtitle && <p className="text-xs text-muted-foreground"><Link prefetch={false} href={`/artists/${artist.id}`} className="underline-offset-4 hover:underline">{subtitle}</Link></p>}</TableCell>
      <TableCell className="w-24 px-4 py-3 text-right font-heading text-lg font-bold tabular-nums">{row.wins}</TableCell>
    </TableRow>
  );
}

function MobileLeaderboardRow({ row, kind }: { row: ArtistLeaderboardRow | SongLeaderboardRow; kind: "artist" | "song" }) {
  const { title, subtitle, artist, songId } = leaderboardCopy(row, kind);
  return <div className="mobile-record items-center gap-3 border-b border-border/70 px-3 py-3"><RankMarker rank={row.rank} /><div className="min-w-0 flex-1"><p className="truncate font-semibold">{kind === "artist" ? <Link prefetch={false} href={`/artists/${artist.id}`}>{title}</Link> : <Link prefetch={false} href={`/songs/${songId}`}>{title}</Link>}</p>{subtitle && <p className="truncate text-xs text-muted-foreground"><Link prefetch={false} href={`/artists/${artist.id}`}>{subtitle}</Link></p>}</div><p className="font-heading text-lg font-bold tabular-nums"><span className="sr-only">{row.wins} wins</span>{row.wins}</p></div>;
}

export function Leaderboard({ rows, kind, empty = "No wins to show yet." }: { rows: (ArtistLeaderboardRow | SongLeaderboardRow)[]; kind: "artist" | "song"; empty?: string }) {
  if (!rows.length) return <EmptyState message={empty} />;
  return (
    <div className="overflow-hidden border border-border bg-card">
      <Table className="desktop-table w-full border-collapse text-sm">
        <TableCaption className="sr-only">Top five {kind === "artist" ? "artists" : "songs"} by music show wins</TableCaption>
        <TableHeader><TableRow className="border-foreground border-b-2 bg-muted/50 text-left text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-16 px-4 py-3">Rank</TableHead><TableHead className="px-4 py-3">{kind === "artist" ? "Artist" : "Song"}</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader>
        <TableBody>{rows.map((row, index) => <DesktopLeaderboardRow key={`${kind}-${index}-${row.rank}`} row={row} kind={kind} />)}</TableBody>
      </Table>
      <div className="mobile-record flex-col"><div className="flex items-center justify-between border-b-2 border-foreground bg-muted/50 px-3 py-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground"><span>Rank · {kind}</span><span>Wins</span></div>{rows.map((row, index) => <MobileLeaderboardRow key={`${kind}-mobile-${index}-${row.rank}`} row={row} kind={kind} />)}</div>
    </div>
  );
}

export function WinRecord({ win, hideArtist = false, hideSong = false }: { win: Win; hideArtist?: boolean; hideSong?: boolean }) {
  return (
    <article className="border-b border-border/70 px-3 py-3 last:border-b-0">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3 gap-y-2">
        <time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time>
        {!hideSong && <div className="col-span-2 row-start-2 min-w-0"><p className="break-words font-semibold"><Link prefetch={false} href={`/songs/${win.song.id}`} className="underline-offset-4 hover:underline">{win.song.title}</Link></p>{!hideArtist && <p className="break-words text-xs text-muted-foreground"><Link prefetch={false} href={`/artists/${win.song.artist.id}`} className="underline-offset-4 hover:underline">{win.song.artist.name}</Link></p>}</div>}
        <ShowBadge slug={win.show.slug} name={win.show.name} />
      </div>
      <MobileWinVideoDisclosure win={win} className="mt-3" />
    </article>
  );
}

export function RecentWins({ wins }: { wins: Win[] }) {
  if (!wins.length) {
    return <EmptyState message="No recent wins are available right now." />;
  }
  return <div className="border border-border bg-card">
    <Table className="desktop-table border-collapse">
      <TableCaption className="sr-only">Most recent music show wins</TableCaption>
      <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-32 px-4 py-3">Date</TableHead><TableHead className="px-4 py-3">Song</TableHead><TableHead className="px-4 py-3">Artist</TableHead><TableHead className="w-44 px-4 py-3 text-right">Music show</TableHead><TableHead className="w-44 px-4 py-3 text-right">Video</TableHead></TableRow></TableHeader>
      <TableBody>{wins.map((win) => <DesktopWinVideoRow key={win.id} win={win} colSpan={5}><TableCell className="px-4 py-3"><time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time></TableCell><TableCell className="px-4 py-3"><Link prefetch={false} href={`/songs/${win.song.id}`} className="font-semibold underline-offset-4 hover:underline">{win.song.title}</Link></TableCell><TableCell className="px-4 py-3"><Link prefetch={false} href={`/artists/${win.song.artist.id}`} className="underline-offset-4 hover:underline">{win.song.artist.name}</Link></TableCell><TableCell className="w-44 px-4 py-3 text-right"><ShowBadge slug={win.show.slug} name={win.show.name} /></TableCell></DesktopWinVideoRow>)}</TableBody>
    </Table>
    <div className="mobile-record flex-col">{wins.map((win) => <WinRecord key={win.id} win={win} />)}</div>
  </div>;
}

export function MusicShowList({ shows }: { shows: Show[] }) {
  if (!shows.length) {
    return <EmptyState message="Music show information is unavailable right now." />;
  }

  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {shows.map((show) => (
        <li key={show.id}>
          <Link prefetch={false}
            href={`/wins?show=${encodeURIComponent(show.slug)}#wins-results-title`}
            aria-label={`View ${show.name} wins`}
            className="flex items-center justify-between gap-4 border-2 border-foreground bg-card p-4 transition-colors hover:bg-accent focus-visible:bg-accent"
          >
            <ShowBadge slug={show.slug} name={show.name} />
            <span className="text-xs tabular-nums text-muted-foreground">{show.total_wins} wins</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="border border-dashed border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">{message}</div>;
}

export function ErrorState({ messages }: { messages: string[] }) {
  if (!messages.length) return null;
  return (
    <div
      role="alert"
      className="mt-4 border border-border border-l-4 border-l-warning bg-card px-4 py-3 text-sm text-foreground"
    >
      Some results couldn&apos;t load. Refresh the page to try again.
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div role="status" className="border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">{label}</div>;
}
