"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { EmptyState, LoadingState, ShowBadge } from "@/components/data-display";
import { formatDate } from "@/lib/utils";
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
import { archivePageCount } from "@/lib/pagination";
import { usePaginationScroll } from "@/lib/use-pagination-scroll";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DesktopWinVideoRow, MobileWinVideoDisclosure } from "@/components/win-videos";
import { ArchiveResultsSummary } from "@/components/pagination";

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
      <Table className="desktop-table border-collapse">
        <TableCaption className="sr-only">Filtered music show wins</TableCaption>
        <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-32 px-4 py-3">Date</TableHead><TableHead className="px-4 py-3">Artist</TableHead><TableHead className="px-4 py-3">Song</TableHead><TableHead className="w-44 px-4 py-3 text-right">Music show</TableHead><TableHead className="w-24 px-4 py-3 text-right">Video</TableHead></TableRow></TableHeader>
        <TableBody>{wins.map((win) => <DesktopWinVideoRow key={win.id} win={win} colSpan={5} videoCellClassName="w-24 px-4 py-4 text-right"><TableCell className="px-4 py-4"><time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time></TableCell><TableCell className="px-4 py-4"><Link prefetch={false} href={`/artists/${win.song.artist.id}`} className="font-semibold underline-offset-4 hover:underline">{win.song.artist.name}</Link></TableCell><TableCell className="px-4 py-4"><Link prefetch={false} href={`/songs/${win.song.id}`} className="font-medium underline-offset-4 hover:underline">{win.song.title}</Link></TableCell><TableCell className="w-44 px-4 py-4 text-right"><Link prefetch={false} href={`/wins?show=${encodeURIComponent(win.show.slug)}#wins-results-title`} aria-label={`Filter wins by ${win.show.name}`}><ShowBadge slug={win.show.slug} name={win.show.name} /></Link></TableCell></DesktopWinVideoRow>)}</TableBody>
      </Table>
      <div className="mobile-record flex-col">
        {wins.map((win) => <article key={win.id} className="grid gap-2 border-b border-border/70 px-4 py-4 last:border-b-0"><time dateTime={win.date} className="font-heading text-sm font-bold tabular-nums text-muted-foreground">{formatDate(win.date)}</time><Link prefetch={false} href={`/artists/${win.song.artist.id}`} className="min-w-0 font-semibold underline-offset-4 hover:underline">{win.song.artist.name}</Link><Link prefetch={false} href={`/songs/${win.song.id}`} className="min-w-0 font-medium underline-offset-4 hover:underline">{win.song.title}</Link><Link prefetch={false} href={`/wins?show=${encodeURIComponent(win.show.slug)}#wins-results-title`} aria-label={`Filter wins by ${win.show.name}`}><ShowBadge slug={win.show.slug} name={win.show.name} /></Link><MobileWinVideoDisclosure win={win} /></article>)}
      </div>
    </div>
  );
}

export function WinsExplorer() {
  const searchParams = useSearchParams();
  const filters = winsFiltersFromSearchParams(searchParams);
  const filtersRef = useRef(filters);
  useEffect(() => { filtersRef.current = filters; }, [filters]);
  const dateRangeError = winsDateRangeError(filters);
  const shows = useQuery(showsQueryOptions(browserTransport));
  const wins = useQuery({ ...winsQueryOptions(filters, browserTransport), enabled: !dateRangeError, placeholderData: keepPreviousData });
  const { requestPaginationScroll, cancelPaginationScroll } = usePaginationScroll(filters.page, Boolean(wins.data) && !wins.isPlaceholderData && !wins.isFetching, "wins-results-title");
  const write = useCallback((update: Partial<WinsFilters>, mode: "push" | "replace" = "push") => writeWinsHistory(filtersRef.current, update, mode), []);
  const apply = useCallback((update: Partial<WinsFilters>) => { cancelPaginationScroll(); return write(update); }, [cancelPaginationScroll, write]);
  const paginate = useCallback((page: number) => {
    requestPaginationScroll(page);
    if (!write({ page })) cancelPaginationScroll();
  }, [cancelPaginationScroll, requestPaginationScroll, write]);
  const applySearch = useCallback((search: string) => {
    cancelPaginationScroll();
    if (search.trim() === filtersRef.current.search) return;
    write(search ? { search } : { search: "" }, "replace");
  }, [cancelPaginationScroll, write]);
  const clearFilters = useCallback(() => {
    cancelPaginationScroll();
    const navigation = clearWinsNavigation(filtersRef.current);
    if (navigation) window.history.pushState(null, "", navigation.url);
  }, [cancelPaginationScroll]);
  const activeFilters = hasActiveWinsFilters(filters);
  const showOptions: Show[] = shows.data?.results ?? [];
  const data = wins.data;

  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">Music show wins</h1>
        <p className="mt-2 max-w-2xl text-surface-berry-foreground/80">Search results by artist, song, show, year, or date.</p>
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
        {shows.isError && <p role="status" className="mt-3 text-sm text-destructive">The music show filter couldn&apos;t load. The other filters still work.</p>}
        {dateRangeError && <p role="alert" className="mt-3 border-l-4 border-destructive bg-danger-surface px-3 py-2 text-sm">{dateRangeError}</p>}
      </section>

      <section className="mt-8" aria-labelledby="wins-results-title">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b-2 border-foreground pb-3">
          <div><h2 id="wins-results-title" className="scroll-mt-24 font-heading text-2xl font-bold">Results</h2>{wins.isFetching && data && <p role="status" className="mt-1 text-xs text-muted-foreground">Updating results…</p>}</div>
          {data && <ArchiveResultsSummary totalCount={data.count} page={filters.page} resultCount={data.results.length} singular="win" plural="wins" />}
        </div>
        {dateRangeError ? null : wins.isLoading && !data ? <LoadingState label="Loading wins…" /> : wins.isError ? (
          <div role="alert" className="border border-destructive bg-danger-surface p-4"><p className="font-semibold">Wins couldn&apos;t load. Your filters are unchanged.</p><button type="button" onClick={() => wins.refetch()} className="mt-3 min-h-10 border-2 border-foreground bg-card px-3 text-sm font-bold">Try again</button></div>
        ) : data?.results.length ? <WinsRows wins={data.results} /> : <EmptyState message="No wins match these filters." />}
        {data && !dateRangeError && (data.previous || data.next) && <nav aria-label="Wins pages" className="mt-6 flex items-center justify-between gap-4">
          {data.previous ? <button type="button" onClick={() => paginate(filters.page - 1)} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Previous</button> : <span />}
          <span className="text-sm font-semibold tabular-nums">Page {filters.page} of {archivePageCount(data.count)}</span>
          {data.next ? <button type="button" onClick={() => paginate(filters.page + 1)} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Next</button> : <span />}
        </nav>}
      </section>
    </main>
  );
}
