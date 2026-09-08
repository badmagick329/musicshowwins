"use client";

import { useEffect, useRef, useState } from "react";
import type { Artist, Win } from "@/lib/api-shared";
import { artistYears, datedArtistWins, parseArtistYear } from "@/lib/artist-years";
import { ArtistYearResults } from "@/components/artist-year-results";

type Plausible = ((event: string, options: { props: Record<string, string> }) => void) & { q?: unknown[] };
const control = "min-h-11 border border-foreground bg-card px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground";

export function ArtistWinsByYear({ artist, wins, initialYear }: { artist: Artist; wins: Win[]; initialYear: string | null }) {
  const [year, setYear] = useState(initialYear);
  const chartRef = useRef<HTMLDivElement>(null);
  const selectedBarRef = useRef<HTMLButtonElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const [resultsMinHeight, setResultsMinHeight] = useState(0);
  const dated = datedArtistWins(wins);
  const years = artistYears(dated);
  const selected = dated.filter((win) => !year || win.date.startsWith(`${year}-`));
  const max = Math.max(1, ...years.map((item) => item.count));
  const winningSongs = new Set(selected.map((win) => win.song.id)).size;

  useEffect(() => {
    const restore = () => {
      setResultsMinHeight(Math.max(0, window.innerHeight - resultsRef.current!.getBoundingClientRect().top));
      setYear(parseArtistYear(new URLSearchParams(window.location.search).get("year") ?? undefined));
    };
    restore();
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const bar = selectedBarRef.current;
    if (!chart) return;
    // Move only the chart's horizontal viewport; selecting a year never scrolls the page.
    chart.scrollLeft = bar
      ? chart.scrollLeft + bar.getBoundingClientRect().left - chart.getBoundingClientRect().left - (chart.clientWidth - bar.clientWidth) / 2
      : 0;
  }, [year]);

  function track(event: string, selectedYear = year, extra: Record<string, string> = {}) {
    const analytics = window as Window & { plausible?: Plausible };
    // Preserve deliberate interactions while the deferred Plausible script loads.
    analytics.plausible ??= Object.assign((...args: Parameters<Plausible>) => {
      analytics.plausible!.q!.push(args);
    }, { q: [] as unknown[] });
    analytics.plausible(event, {
      props: { artist: artist.name, artist_id: String(artist.id), year: selectedYear ?? "all", ...extra },
    });
  }

  function selectYear(value: string | null, source: string) {
    if (value === year) return;
    // Short results must not shrink the document past the current viewport and clamp its scroll position.
    setResultsMinHeight(Math.max(0, window.innerHeight - resultsRef.current!.getBoundingClientRect().top));
    const url = new URL(window.location.href);
    if (value) url.searchParams.set("year", value);
    else url.searchParams.delete("year");
    window.history.pushState(null, "", url);
    setYear(value);
    track("Artist year selected", value, { source });
  }

  return <>
    <section className="mt-10" aria-labelledby="years-title">
      <div className="flex flex-col gap-3 border-b-2 border-foreground pb-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6">
        <h2 id="years-title" className="font-heading text-2xl font-bold">Wins by year</h2>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <label htmlFor="artist-year" className="font-semibold">Year</label>
          <select id="artist-year" value={year ?? "all"} onChange={(event) => selectYear(event.target.value === "all" ? null : event.target.value, "selector")} className={control}>
            <option value="all">All years</option>
            {year && !years.some((item) => item.year === year) && <option value={year}>{year} — 0 recorded wins</option>}
            {years.map((item) => <option key={item.year} value={item.year}>{item.year} — {item.count} recorded {item.count === 1 ? "win" : "wins"}</option>)}
          </select>
          {year && <button type="button" className="min-h-11 px-1 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground" onClick={() => selectYear(null, "all-years")}>Reset to all years</button>}
        </div>
      </div>
      {dated.length < wins.length && <p className="mt-3 text-sm text-muted-foreground">Undated history is excluded.</p>}
      {years.length ? <>
        <p className="mt-3 text-center text-sm text-muted-foreground">Select a year to explore its wins.{years.length > 5 && <span className="block sm:hidden">Swipe the chart to see more years.</span>}</p>
        <div ref={chartRef} className="mx-auto mt-2 overflow-x-auto overscroll-x-contain p-1" style={{ maxWidth: `${Math.min(60, Math.max(2, years.length) * 6)}rem` }}>
          <ul aria-label="Recorded wins per year" className="flex w-full" style={{ minWidth: `${years.length * 3.5}rem` }}>
            {years.map((item) => <li key={item.year} className="min-w-14 flex-1">
              <button ref={year === item.year ? selectedBarRef : undefined} type="button" aria-label={`${item.year}: ${item.count} recorded ${item.count === 1 ? "win" : "wins"}`} aria-pressed={year === item.year} onClick={() => selectYear(item.year, "chart")} className="group flex w-full cursor-pointer flex-col items-center focus-visible:outline-offset-[-2px]">
                <span className="flex h-48 w-full flex-col items-center justify-end border-b border-foreground">
                  <span className="mb-1 text-sm font-bold tabular-nums">{item.count}</span>
                  <span aria-hidden="true" className={`w-2/3 max-w-16 ${year === item.year ? "bg-primary group-hover:opacity-90" : "bg-surface-berry group-hover:bg-section-ink"}`} style={{ height: `${item.count / max * 160}px` }} />
                </span>
                <span className={`flex h-11 items-center text-sm font-semibold tabular-nums ${year === item.year ? "underline decoration-2 underline-offset-4" : ""}`}>{item.year}</span>
              </button>
            </li>)}
          </ul>
        </div>
      </> : <p className="mt-5">No dated wins are recorded for this artist yet. A yearly chart is not available.</p>}
    </section>
    <div ref={resultsRef} style={{ minHeight: resultsMinHeight }} onClick={(event) => {
      const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="/songs/"]');
      if (link) track("Artist year song opened", year, { song_id: link.getAttribute("href")!.split("/")[2] });
    }}>
      <div className="mt-3" role="status" aria-live="polite" aria-atomic="true">
        <h2 className="font-heading text-xl font-semibold">{year ? `Wins in ${year}` : "Wins across all years"}</h2>
        {year && !selected.length ? <p className="mt-1">No wins are recorded for {year}.</p> : <p className="mt-1"><strong>{selected.length}</strong> recorded {selected.length === 1 ? "win" : "wins"} · <strong>{winningSongs}</strong> winning {winningSongs === 1 ? "song" : "songs"}</p>}
      </div>
      {selected.length > 0 && <ArtistYearResults key={year ?? "all"} wins={selected} />}
    </div>
  </>;
}
