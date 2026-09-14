"use client";

import Link from "next/link";

type Plausible = ((event: string, options: { props: Record<string, string> }) => void) & { q?: unknown[] };

const eventName = "Top wins this year clicked";

function trackClick() {
  const analytics = window as Window & { plausible?: Plausible };
  analytics.plausible ??= Object.assign((...args: Parameters<Plausible>) => {
    analytics.plausible!.q!.push(args);
  }, { q: [] as unknown[] });
  analytics.plausible(eventName, { props: {} });
}

export function TopWinsThisYearLink() {
  return <Link href="/rankings" onClick={trackClick} className="mt-6 inline-flex min-h-11 items-center border-2 border-surface-berry-foreground bg-highlight-yellow px-4 text-sm font-bold text-foreground shadow-[3px_3px_0_var(--section-ink)] transition-transform hover:-translate-y-0.5">Top wins this year →</Link>;
}
