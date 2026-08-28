import type {
  ArtistLeaderboardRow,
  Show,
  SongLeaderboardRow,
  Win,
} from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

export function ShowBadge({ slug, name }: { slug: string; name?: string }) {
  const showClass = `show-${slug}`;
  return (
    <span className={cn("show-badge inline-flex items-center gap-1.5 border px-2 py-0.5 text-xs font-bold", showClass)}>
      <span className="show-dot size-1.5 rounded-full" aria-hidden="true" />
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
  return { title, subtitle, artist };
}

function DesktopLeaderboardRow({ row, kind }: { row: ArtistLeaderboardRow | SongLeaderboardRow; kind: "artist" | "song" }) {
  const { title, subtitle, artist } = leaderboardCopy(row, kind);
  return (
    <TableRow className="border-border/70 transition-colors hover:bg-accent/60">
      <TableCell className="w-16 px-4 py-3"><RankMarker rank={row.rank} /></TableCell>
      <TableCell className="px-4 py-3"><p className="font-semibold">{kind === "artist" ? <Link href={`/artists/${artist.id}`} className="underline-offset-4 hover:underline">{title}</Link> : title}</p>{subtitle && <p className="text-xs text-muted-foreground"><Link href={`/artists/${artist.id}`} className="underline-offset-4 hover:underline">{subtitle}</Link></p>}</TableCell>
      <TableCell className="w-24 px-4 py-3 text-right font-heading text-lg font-bold tabular-nums">{row.wins}</TableCell>
    </TableRow>
  );
}

function MobileLeaderboardRow({ row, kind }: { row: ArtistLeaderboardRow | SongLeaderboardRow; kind: "artist" | "song" }) {
  const { title, subtitle, artist } = leaderboardCopy(row, kind);
  return <div className="mobile-record items-center gap-3 border-b border-border/70 px-3 py-3"><RankMarker rank={row.rank} /><div className="min-w-0 flex-1"><p className="truncate font-semibold">{kind === "artist" ? <Link href={`/artists/${artist.id}`}>{title}</Link> : title}</p>{subtitle && <p className="truncate text-xs text-muted-foreground"><Link href={`/artists/${artist.id}`}>{subtitle}</Link></p>}</div><p className="font-heading text-lg font-bold tabular-nums"><span className="sr-only">{row.wins} wins</span>{row.wins}</p></div>;
}

export function Leaderboard({ rows, kind, empty = "No wins to show yet." }: { rows: (ArtistLeaderboardRow | SongLeaderboardRow)[]; kind: "artist" | "song"; empty?: string }) {
  if (!rows.length) return <EmptyState message={empty} />;
  return (
    <div className="overflow-hidden border border-border bg-card">
      <Table className="desktop-table w-full border-collapse text-sm">
        <TableHeader><TableRow className="border-foreground border-b-2 bg-muted/50 text-left text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-16 px-4 py-3">Rank</TableHead><TableHead className="px-4 py-3">{kind === "artist" ? "Artist" : "Song"}</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader>
        <TableBody>{rows.map((row, index) => <DesktopLeaderboardRow key={`${kind}-${index}-${row.rank}`} row={row} kind={kind} />)}</TableBody>
      </Table>
      <div className="mobile-record flex-col"><div className="flex items-center justify-between border-b-2 border-foreground bg-muted/50 px-3 py-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground"><span>Rank · {kind}</span><span>Wins</span></div>{rows.map((row, index) => <MobileLeaderboardRow key={`${kind}-mobile-${index}-${row.rank}`} row={row} kind={kind} />)}</div>
    </div>
  );
}

export function WinRecord({ win, hideArtist = false }: { win: Win; hideArtist?: boolean }) {
  return (
    <article className="flex items-start gap-3 border-b border-border/70 px-3 py-3 last:border-b-0 sm:items-center">
      <time dateTime={win.date} className="w-20 shrink-0 font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time>
      <div className="min-w-0 flex-1"><p className="truncate font-semibold">{win.song.title}</p>{!hideArtist && <p className="truncate text-xs text-muted-foreground"><Link href={`/artists/${win.song.artist.id}`} className="underline-offset-4 hover:underline">{win.song.artist.name}</Link></p>}</div>
      <ShowBadge slug={win.show.slug} name={win.show.name} />
    </article>
  );
}

export function RecentWins({ wins }: { wins: Win[] }) {
  if (!wins.length) {
    return <EmptyState message="No recent wins are available right now." />;
  }
  return <div className="border border-border bg-card">{wins.map((win) => <WinRecord key={win.id} win={win} />)}</div>;
}

export function MusicShowList({ shows }: { shows: Show[] }) {
  if (!shows.length) {
    return <EmptyState message="No music-show information is available right now." />;
  }

  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {shows.map((show) => (
        <li
          key={show.id}
          className="flex items-center justify-between gap-4 border-2 border-foreground bg-card p-4"
        >
          <ShowBadge slug={show.slug} name={show.name} />
          <span className="text-xs text-muted-foreground">
            {show.active ? "Active weekly show" : "Historical show"}
          </span>
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
      We couldn’t load the archive data. Try refreshing the page in a moment.
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div role="status" className="border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">{label}</div>;
}

export function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}
