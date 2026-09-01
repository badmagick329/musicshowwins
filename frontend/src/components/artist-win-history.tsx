import type { Win } from "@/lib/api-shared";
import { EmptyState, ShowBadge, WinRecord } from "@/components/data-display";
import { DesktopWinVideoRow } from "@/components/win-videos";
import { formatDate } from "@/lib/utils";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Link from "next/link";

export function ArtistWinHistory({ wins, emptyMessage = "No wins with dates are recorded for this artist.", hideSong = false }: { wins: Win[]; emptyMessage?: string; hideSong?: boolean }) {
  if (!wins.length) return <EmptyState message={emptyMessage} />;
  return <div className="border border-border bg-card">
    <Table className="desktop-table border-collapse">
      <TableCaption className="sr-only">Music show win history by date</TableCaption>
      <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-32 px-4 py-3">Date</TableHead>{!hideSong && <TableHead className="px-4 py-3">Song</TableHead>}<TableHead className="w-44 px-4 py-3 text-right">Music show</TableHead><TableHead className="w-44 px-4 py-3 text-right">Video</TableHead></TableRow></TableHeader>
      <TableBody>{wins.map((win) => <DesktopWinVideoRow key={win.id} win={win} colSpan={hideSong ? 3 : 4}><TableCell className="px-4 py-3"><time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time></TableCell>{!hideSong && <TableCell className="px-4 py-3"><Link prefetch={false} href={`/songs/${win.song.id}`} className="font-semibold underline-offset-4 hover:underline">{win.song.title}</Link></TableCell>}<TableCell className="w-44 px-4 py-3 text-right"><ShowBadge slug={win.show.slug} name={win.show.name} /></TableCell></DesktopWinVideoRow>)}</TableBody>
    </Table>
    <div className="mobile-record flex-col">{wins.map((win) => <WinRecord key={win.id} win={win} hideArtist hideSong={hideSong} />)}</div>
  </div>;
}
