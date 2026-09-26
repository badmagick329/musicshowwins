import Link from "next/link";
import type { ArchiveWeek, Show } from "@/lib/api-shared";
import { FactLabel, SectionHeading } from "@/components/data-display";
import { MobileWinVideoDisclosure } from "@/components/win-videos";
import { buildWeek, formatSlotDay, formatWeekRange } from "@/lib/this-week";
import { cardFacts } from "@/lib/win-facts";
import { cn } from "@/lib/utils";
import { artistPath } from "@/lib/paths";

export function ThisWeek({ week, shows, today }: { week: ArchiveWeek; shows: Show[]; today: string }) {
  const slots = buildWeek(week, shows, today);
  const range = formatWeekRange(week.start, week.end);
  return (
    <section id="this-week" className="mt-14">
      <SectionHeading title={week.current ? `This week · ${range}` : `Latest results · ${range}`} action={<Link href="/wins" className="compact-link-target text-sm font-bold text-link-pink">View all wins</Link>} />
      {!week.current && <p className="-mt-1 mb-4 text-sm text-muted-foreground">No results yet this week.</p>}
      <ol aria-label="Music show results by broadcast day" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {slots.map((slot) => (
          <li key={slot.slug} className={cn("show-strip-cell border border-border bg-card px-4 pb-3", `show-${slot.slug}`)}>
            <p className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-semibold">{slot.name}</span>
              <time dateTime={slot.date} className="tabular-nums text-muted-foreground">{formatSlotDay(slot.date)}</time>
            </p>
            {slot.status === "won" ? slot.wins.map((win) => {
              const facts = cardFacts(win);
              return (
                <div key={win.id} className="mt-1.5">
                  <p className="leading-snug"><Link prefetch={false} href={`/songs/${win.song.id}`} className="compact-link-target font-heading text-lg font-bold">{win.song.title}</Link><span aria-hidden="true" className="text-muted-foreground"> · </span><Link prefetch={false} href={artistPath(win.song.artist)} className="compact-link-target text-sm">{win.song.artist.name}</Link></p>
                  {(facts.count || facts.tag) && <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">{facts.count && <span>{facts.count}</span>}{facts.tag && <FactLabel>{facts.tag}</FactLabel>}</p>}
                  <MobileWinVideoDisclosure win={win} className="mt-2.5 items-start" />
                </div>
              );
            }) : (
              <p className="mt-1 text-sm text-muted-foreground">
                {slot.status === "upcoming" ? (slot.date === today ? "Airs today" : "Upcoming") : week.current ? "No result yet" : "No result recorded"}
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
