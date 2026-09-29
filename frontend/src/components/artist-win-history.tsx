import Link from "next/link";
import type { Win } from "@/lib/api-shared";
import { EmptyState, ShowBadge, WinFactTag } from "@/components/data-display";
import { WinVideoControl } from "@/components/win-videos";
import { cn, formatDate } from "@/lib/utils";

// Each win is rendered once: a card on phones, a table-like row from `md` up. A hidden
// desktop table plus a mobile copy doubled every row in the HTML search engines read,
// which made already short pages look thinner and more repetitive.
export function ArtistWinHistory({ wins, emptyMessage = "No wins with dates are recorded for this artist.", hideSong = false }: { wins: Win[]; emptyMessage?: string; hideSong?: boolean }) {
  if (!wins.length) return <EmptyState message={emptyMessage} />;
  const columns = hideSong ? "md:grid-cols-[minmax(0,1fr)_11rem_13rem]" : "md:grid-cols-[8rem_minmax(0,1fr)_11rem_13rem]";
  return <div className="border border-border bg-card">
    <div aria-hidden="true" className={cn("hidden border-b-2 bg-muted/50 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground md:grid", columns)}>
      <span className="px-4 py-3">Date</span>{!hideSong && <span className="px-4 py-3">Song</span>}<span className="px-4 py-3 text-right">Music show</span><span className="px-4 py-3 text-right">Video</span>
    </div>
    <ol aria-label="Music show win history by date">
      {wins.map((win) => <li key={win.id} id={`win-${win.id}`} className="scroll-mt-24 border-b border-border/70 last:border-b-0 md:hover:bg-accent/60">
        <article className={cn("grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3 gap-y-2 px-3 py-3 md:items-center md:gap-0 md:p-0", columns)}>
          <div className="md:px-4 md:py-3"><time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time>{hideSong && <WinFactTag win={win} />}</div>
          {!hideSong && <div className="col-span-2 row-start-2 min-w-0 md:col-span-1 md:row-start-auto md:px-4 md:py-3"><Link prefetch={false} href={`/songs/${win.song.id}`} className="compact-link-target break-words font-semibold">{win.song.title}</Link><WinFactTag win={win} /></div>}
          <div className="md:px-4 md:py-3 md:text-right"><ShowBadge slug={win.show.slug} name={win.show.name} /></div>
          <WinVideoControl win={win} className="col-span-2 mt-1" />
        </article>
      </li>)}
    </ol>
  </div>;
}
