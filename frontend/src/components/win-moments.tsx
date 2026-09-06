"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import type { Win } from "@/lib/api-shared";
import { ShowBadge } from "@/components/data-display";
import { formatDate } from "@/lib/utils";

const DEFAULT_VISIBLE_MOMENTS = 2;

export function WinMoments({ wins }: { wins: Win[] }) {
  const [expanded, setExpanded] = useState(false);
  const moments = wins
    .filter((win) => win.moment)
    .toSorted((a, b) => a.date.localeCompare(b.date));
  if (!moments.length) return null;

  const remaining = moments.length - DEFAULT_VISIBLE_MOMENTS;

  return (
    <section className="mt-12" aria-labelledby="moments-title">
      <h2 id="moments-title" className="mb-4 border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">
        Notable moments
      </h2>
      <div id="additional-moments" className="grid gap-5">
        {moments.map((win, index) => (
          <article
            key={win.id}
            hidden={!expanded && index >= DEFAULT_VISIBLE_MOMENTS}
            className="border border-border bg-card p-5 sm:p-6"
          >
            <h3 className="font-heading text-xl font-bold">{win.moment!.heading}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <time dateTime={win.date}>{formatDate(win.date)}</time>
              <span aria-hidden="true">·</span>
              <Link prefetch={false} href={`/songs/${win.song.id}`} className="font-semibold text-foreground underline-offset-4 hover:underline">
                {win.song.title}
              </Link>
              <span aria-hidden="true">·</span>
              <ShowBadge slug={win.show.slug} name={win.show.name} />
            </div>
            <p className="mt-4 max-w-3xl leading-7">{win.moment!.body}</p>
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              <Link href={`#win-${win.id}`} className="hidden font-semibold underline-offset-4 hover:underline sm:inline">View this win</Link>
              <Link href={`#win-mobile-${win.id}`} className="font-semibold underline-offset-4 hover:underline sm:hidden">View this win</Link>
              {win.moment!.citations.map((citation) => (
                <a key={citation.id} href={citation.url} target="_blank" rel="noreferrer" className="inline-flex min-w-0 items-center gap-1 font-semibold underline-offset-4 hover:underline">
                  <span className="break-words">{citation.publisher_name || citation.provider} — {citation.title}</span>
                  <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
                </a>
              ))}
            </div>
          </article>
        ))}
      </div>
      {remaining > 0 && (
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls="additional-moments"
          aria-label={expanded ? "Show fewer notable moments" : `Show ${remaining} more notable ${remaining === 1 ? "moment" : "moments"}`}
          onClick={() => setExpanded((value) => !value)}
          className="mt-4 inline-flex min-h-11 items-center gap-2 border border-foreground bg-card px-4 py-2 font-semibold transition-colors hover:bg-accent focus-visible:bg-accent"
        >
          {expanded ? "Show fewer" : `${remaining} more`}
          {expanded ? <ChevronUp aria-hidden="true" className="size-4" /> : <ChevronDown aria-hidden="true" className="size-4" />}
        </button>
      )}
    </section>
  );
}
