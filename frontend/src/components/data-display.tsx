import type {
  ArtistLeaderboardRow,
  Show,
  SongLeaderboardRow,
  Win,
} from "@/lib/api-shared";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { notableTag } from "@/lib/win-facts";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { artistPath } from "@/lib/paths";

export function SectionHeading({ title, action, level = 2 }: { title: string; action?: React.ReactNode; level?: 2 | 3 }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4 border-b-2 pb-3">
      {level === 2 ? <h2 className="font-heading text-xl font-bold tracking-tight sm:text-2xl">{title}</h2> : <h3 className="font-heading text-xl font-bold tracking-tight sm:text-2xl">{title}</h3>}
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

// A gap-px grid draws single dividers at every column count, so tiles can reflow
// from two columns on phones to four on desktop without per-breakpoint borders.
export function MetricGrid({ children }: { children: React.ReactNode }) {
  return <dl className="grid grid-cols-2 gap-px border border-border bg-border lg:grid-cols-4">{children}</dl>;
}

export function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="min-w-0 bg-card p-4"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-heading text-xl font-bold tabular-nums sm:text-2xl">{value}</dd></div>;
}

// At most six shows exist, so one compact row replaces a tall two-column table.
// Cells draw their own outlines (overlapping across the 1px gap) so unused tracks
// stay page-coloured when an artist has won on fewer shows.
export function ShowWinsStrip({ shows, label }: { shows: { id: number; slug: string; name: string; wins: number }[]; label: string }) {
  return (
    <ul aria-label={label} className="grid grid-cols-2 gap-px p-px sm:grid-cols-3 lg:grid-cols-6">
      {shows.map((show) => (
        <li key={show.id} className={cn("show-strip-cell bg-card px-4 py-3 outline outline-1 outline-border", `show-${show.slug}`)}>
          <span className="block text-sm font-semibold">{show.name}</span>
          <span className="font-heading text-2xl font-bold tabular-nums">{show.wins}</span>
          <span className="sr-only"> {show.wins === 1 ? "win" : "wins"}</span>
        </li>
      ))}
    </ul>
  );
}

// Shown on only the few notable rows so long histories stay scannable.
export function WinFactTag({ win }: { win: Win }) {
  const tag = notableTag(win);
  return tag ? <span className="mt-1 block"><FactLabel>{tag}</FactLabel></span> : null;
}

export function FactLabel({ children }: { children: React.ReactNode }) {
  return <span className="inline-block border border-highlight-yellow bg-highlight-yellow/25 px-1.5 py-0.5 text-xs font-semibold text-foreground">{children}</span>;
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

// Three narrow columns fit a phone, so one table serves every width; duplicated
// desktop and mobile markup doubled the text search engines read.
export function Leaderboard({ rows, kind, empty = "No wins to show yet." }: { rows: (ArtistLeaderboardRow | SongLeaderboardRow)[]; kind: "artist" | "song"; empty?: string }) {
  if (!rows.length) return <EmptyState message={empty} />;
  return (
    <div className="overflow-hidden border border-border bg-card">
      <Table className="w-full border-collapse text-sm">
        <TableCaption className="sr-only">Top five {kind === "artist" ? "artists" : "songs"} by music show wins</TableCaption>
        <TableHeader><TableRow className="border-b-2 bg-muted/50 text-left text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-14 px-3 py-3 sm:w-16 sm:px-4">Rank</TableHead><TableHead className="px-3 py-3 sm:px-4">{kind === "artist" ? "Artist" : "Song"}</TableHead><TableHead className="w-20 px-3 py-3 text-right sm:w-24 sm:px-4">Wins</TableHead></TableRow></TableHeader>
        <TableBody>{rows.map((row, index) => {
          const { title, subtitle, artist, songId } = leaderboardCopy(row, kind);
          return <TableRow key={`${kind}-${index}-${row.rank}`} className="border-border/70 transition-colors hover:bg-accent/60">
            <TableCell className="px-3 py-3 sm:px-4"><RankMarker rank={row.rank} /></TableCell>
            <TableCell className="whitespace-normal break-words px-3 py-3 sm:px-4"><p className="font-semibold">{kind === "artist" ? <Link prefetch={false} href={artistPath(artist)} className="compact-link-target">{title}</Link> : <Link prefetch={false} href={`/songs/${songId}`} className="compact-link-target">{title}</Link>}</p>{subtitle && <p className="text-xs text-muted-foreground"><Link prefetch={false} href={artistPath(artist)} className="compact-link-target">{subtitle}</Link></p>}</TableCell>
            <TableCell className="px-3 py-3 text-right font-heading text-lg font-bold tabular-nums sm:px-4">{row.wins}</TableCell>
          </TableRow>;
        })}</TableBody>
      </Table>
    </div>
  );
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
            className="flex items-center justify-between gap-4 border-2 bg-card p-4 transition-colors hover:bg-accent focus-visible:bg-accent"
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
