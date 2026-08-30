"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { EmptyState, LoadingState, ShowBadge, formatDate } from "@/components/data-display";
import { browserTransport } from "@/lib/api-browser";
import type { Show, Win } from "@/lib/api-shared";
import {
  archiveYears,
  hasActiveWinsFilters,
  winsDateRangeError,
  type WinsFilters,
} from "@/lib/wins-filters";
import { clearWinsNavigation, winsFiltersFromSearchParams, writeWinsHistory } from "@/lib/wins-navigation";
import { showsQueryOptions, winsQueryOptions } from "@/lib/wins-queries";

const pageSize = 100;

function WinsSearchInput({ query, onApply }: { query: string; onApply: (value: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef(query);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    valueRef.current = query;
    if (inputRef.current && inputRef.current.value !== query) inputRef.current.value = query;
  }, [query]);

  useEffect(() => () => { if (timerRef.current) window.clearTimeout(timerRef.current); }, []);

  const onChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    valueRef.current = event.target.value;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => onApply(valueRef.current), 500);
  }, [onApply]);

  return (
    <label className="min-w-0 flex-1 text-sm font-bold">
      Search wins
      <input
        ref={inputRef}
        defaultValue={query}
        onChange={onChange}
        placeholder="Artist or song"
        autoComplete="off"
        className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 text-base font-normal placeholder:text-muted-foreground"
      />
    </label>
  );
}

function WinsRows({ wins }: { wins: Win[] }) {
  return (
    <div className="border border-border bg-card">
      <div className="hidden grid-cols-[7.5rem_minmax(0,1fr)_minmax(0,1fr)_auto] gap-4 border-b-2 border-foreground bg-muted/50 px-4 py-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground md:grid">
        <span>Date</span><span>Artist</span><span>Song</span><span>Music show</span>
      </div>
      {wins.map((win) => (
        <article key={win.id} className="grid gap-2 border-b border-border/70 px-4 py-4 last:border-b-0 md:grid-cols-[7.5rem_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-center md:gap-4">
          <time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time>
          <Link href={`/artists/${win.song.artist.id}`} className="min-w-0 font-semibold underline-offset-4 hover:underline">{win.song.artist.name}</Link>
          <span className="min-w-0 font-medium">{win.song.title}</span>
          <ShowBadge slug={win.show.slug} name={win.show.name} />
        </article>
      ))}
    </div>
  );
}

function ResultsSummary({ count, page, resultCount }: { count: number; page: number; resultCount: number }) {
  if (!count) return <span className="text-sm tabular-nums text-muted-foreground">0 wins</span>;
  const from = (page - 1) * pageSize + 1;
  const to = from + resultCount - 1;
  return <span className="text-sm tabular-nums text-muted-foreground">{count} wins · {from}–{to}</span>;
}

export function WinsExplorer() {
  const searchParams = useSearchParams();
  const filters = winsFiltersFromSearchParams(searchParams);
  const filtersRef = useRef(filters);
  useEffect(() => { filtersRef.current = filters; }, [filters]);
  const dateRangeError = winsDateRangeError(filters);
  const shows = useQuery(showsQueryOptions(browserTransport));
  const wins = useQuery({ ...winsQueryOptions(filters, browserTransport), enabled: !dateRangeError, placeholderData: keepPreviousData });
  const write = useCallback((update: Partial<WinsFilters>, mode: "push" | "replace" = "push") => writeWinsHistory(filtersRef.current, update, mode), []);
  const apply = useCallback((update: Partial<WinsFilters>) => write(update), [write]);
  const applySearch = useCallback((search: string) => {
    if (search.trim() === filtersRef.current.search) return;
    write(search ? { search } : { search: "" }, "replace");
  }, [write]);
  const clearFilters = useCallback(() => {
    const navigation = clearWinsNavigation(filtersRef.current);
    if (navigation) window.history.pushState(null, "", navigation.url);
  }, []);
  const activeFilters = hasActiveWinsFilters(filters);
  const showOptions: Show[] = shows.data?.results ?? [];
  const data = wins.data;

  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">Browse wins</h1>
        <p className="mt-2 max-w-2xl text-surface-berry-foreground/80">Find every dated music-show win in the archive.</p>
      </header>

      <section className="mt-7 border-2 border-foreground bg-search-surface p-4 sm:p-5" aria-label="Filter wins">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <WinsSearchInput query={filters.search} onApply={applySearch} />
          <label className="text-sm font-bold">Music show
            <select value={filters.show} onChange={(event) => apply({ show: event.target.value })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal">
              <option value="">All shows</option>
              {showOptions.map((show) => <option key={show.id} value={show.slug}>{show.name}</option>)}
            </select>
          </label>
          <label className="text-sm font-bold">Year
            <select value={filters.year ?? ""} onChange={(event) => apply({ year: event.target.value ? Number(event.target.value) : undefined })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal">
              <option value="">All years</option>
              {archiveYears().map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
          <label className="text-sm font-bold">Order
            <select value={filters.ordering} onChange={(event) => apply({ ordering: event.target.value as WinsFilters["ordering"] })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal">
              <option value="-date">Newest first</option><option value="date">Oldest first</option>
            </select>
          </label>
          <label className="text-sm font-bold">Date from
            <input type="date" value={filters.dateFrom} onChange={(event) => apply({ dateFrom: event.target.value })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal tabular-nums" />
          </label>
          <label className="text-sm font-bold">Date to
            <input type="date" value={filters.dateTo} onChange={(event) => apply({ dateTo: event.target.value })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal tabular-nums" />
          </label>
          <div className="flex items-end">
            {activeFilters && <button type="button" onClick={clearFilters} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5">Clear filters</button>}
          </div>
        </div>
        {shows.isError && <p role="status" className="mt-3 text-sm text-destructive">Music-show choices could not load. You can still browse all shows.</p>}
        {dateRangeError && <p role="alert" className="mt-3 border-l-4 border-destructive bg-danger-surface px-3 py-2 text-sm">{dateRangeError}</p>}
      </section>

      <section className="mt-8" aria-labelledby="wins-results-title">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b-2 border-foreground pb-3">
          <div><h2 id="wins-results-title" className="font-heading text-2xl font-bold">Results</h2>{wins.isFetching && data && <p role="status" className="mt-1 text-xs text-muted-foreground">Updating results…</p>}</div>
          {data && <ResultsSummary count={data.count} page={filters.page} resultCount={data.results.length} />}
        </div>
        {dateRangeError ? null : wins.isLoading && !data ? <LoadingState label="Loading wins…" /> : wins.isError ? (
          <div role="alert" className="border border-destructive bg-danger-surface p-4"><p className="font-semibold">Wins could not load.</p><button type="button" onClick={() => wins.refetch()} className="mt-3 min-h-10 border-2 border-foreground bg-card px-3 text-sm font-bold">Retry</button></div>
        ) : data?.results.length ? <WinsRows wins={data.results} /> : <EmptyState message="No wins match these filters." />}
        {data && !dateRangeError && (data.previous || data.next) && <nav aria-label="Wins pages" className="mt-6 flex items-center justify-between gap-4">
          {data.previous ? <button type="button" onClick={() => apply({ page: filters.page - 1 })} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Previous</button> : <span />}
          <span className="text-sm font-semibold tabular-nums">Page {filters.page}</span>
          {data.next ? <button type="button" onClick={() => apply({ page: filters.page + 1 })} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Next</button> : <span />}
        </nav>}
      </section>
    </main>
  );
}
