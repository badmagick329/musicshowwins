import Link from "next/link";
import { EmptyState, formatDate, ShowBadge } from "@/components/data-display";
import type { Show } from "@/lib/api-shared";

export function ShowCards({ shows }: { shows: Show[] }) {
  if (!shows.length) {
    return <EmptyState message="Music show information is unavailable right now." />;
  }

  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {shows.map((show) => (
        <article key={show.id} className={`show-${show.slug} relative flex min-w-0 cursor-pointer flex-col border-2 border-foreground bg-card p-5 shadow-[4px_4px_0_var(--show-color)] transition-colors hover:bg-accent`}>
          <div className="flex items-start justify-between gap-4">
            <h2 className="font-heading text-xl font-bold">{show.name}</h2>
            <ShowBadge slug={show.slug} name={show.name} className="shrink-0" />
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-4 border-y border-border py-4">
            <div>
              <dt className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">Recorded wins</dt>
              <dd className="mt-1 font-heading text-3xl font-bold tabular-nums">{show.total_wins}</dd>
            </div>
            <div>
              <dt className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">Win dates</dt>
              <dd className="mt-2 text-sm font-semibold tabular-nums">
                {show.first_win_date && show.latest_win_date
                  ? `${formatDate(show.first_win_date)}–${formatDate(show.latest_win_date)}`
                  : "No win dates recorded"}
              </dd>
            </div>
          </dl>
          <div className="mt-5 min-h-20">
            <h3 className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">Most recent winner</h3>
            {show.latest_win ? (
              <div className="mt-2">
                <p className="font-semibold"><Link prefetch={false} href={`/songs/${show.latest_win.song.id}`} className="relative z-10 underline-offset-4 hover:underline">{show.latest_win.song.title}</Link></p>
                <p className="text-sm text-muted-foreground"><Link prefetch={false} href={`/artists/${show.latest_win.song.artist.id}`} className="relative z-10 underline-offset-4 hover:underline">{show.latest_win.song.artist.name}</Link> · <time dateTime={show.latest_win.date}>{formatDate(show.latest_win.date)}</time></p>
              </div>
            ) : <p className="mt-2 text-sm text-muted-foreground">No wins recorded yet.</p>}
          </div>
          <Link prefetch={false} href={`/wins?show=${encodeURIComponent(show.slug)}#wins-results-title`} className="mt-5 inline-flex min-h-10 items-center justify-center border border-foreground bg-highlight-yellow px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] after:absolute after:inset-0 focus-visible:after:outline-2 focus-visible:after:outline-offset-[-2px] focus-visible:after:outline-brand-pink">View wins</Link>
        </article>
      ))}
    </div>
  );
}
