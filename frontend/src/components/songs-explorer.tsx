"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";
import { EmptyState, LoadingState } from "@/components/data-display";
import { SongResults } from "@/components/song-results";
import { browserTransport } from "@/lib/api-browser";
import { songSortLabels, songSorts, type SongFilters } from "@/lib/song-list";
import { songFiltersFromSearchParams, writeSongHistory } from "@/lib/songs-navigation";
import { songsQueryOptions } from "@/lib/song-queries";
import { archivePageCount } from "@/lib/pagination";
import { usePaginationScroll } from "@/lib/use-pagination-scroll";

function SongSearchInput({ query, onApply }: { query: string; onApply: (value: string) => void }) {
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

  return <label className="min-w-0 flex-1 text-sm font-bold">Search songs<input ref={inputRef} defaultValue={query} onChange={onChange} placeholder="Song or artist" autoComplete="off" className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 text-base font-normal placeholder:text-muted-foreground" /></label>;
}

export function SongsExplorer() {
  const searchParams = useSearchParams();
  const filters = songFiltersFromSearchParams(searchParams);
  const filtersRef = useRef(filters);
  useEffect(() => { filtersRef.current = filters; }, [filters]);
  const songs = useQuery({ ...songsQueryOptions(filters, browserTransport), placeholderData: keepPreviousData });
  const { requestPaginationScroll, cancelPaginationScroll } = usePaginationScroll(filters.page, Boolean(songs.data) && !songs.isPlaceholderData && !songs.isFetching, "song-results-title");
  const write = useCallback((update: Partial<SongFilters>, mode: "push" | "replace" = "push") => writeSongHistory(filtersRef.current, update, mode), []);
  const apply = useCallback((update: Partial<SongFilters>) => { cancelPaginationScroll(); return write(update); }, [cancelPaginationScroll, write]);
  const paginate = useCallback((page: number) => {
    requestPaginationScroll(page);
    if (!write({ page })) cancelPaginationScroll();
  }, [cancelPaginationScroll, requestPaginationScroll, write]);
  const applySearch = useCallback((search: string) => {
    cancelPaginationScroll();
    if (search.trim() === filtersRef.current.search) return;
    write({ search }, "replace");
  }, [cancelPaginationScroll, write]);
  const data = songs.data;

  return <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
    <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8"><h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">Songs</h1><p className="mt-2 max-w-2xl text-surface-berry-foreground/80">Browse winning songs and the artists behind them.</p></header>
    <section className="mt-7 border-2 border-foreground bg-search-surface p-4 sm:p-5" aria-label="Filter songs"><div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_15rem]"><SongSearchInput query={filters.search} onApply={applySearch} /><label className="text-sm font-bold">Sort songs<select value={filters.sort} onChange={(event) => apply({ sort: event.target.value as SongFilters["sort"] })} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal">{songSorts.map((sort) => <option key={sort} value={sort}>{songSortLabels[sort]}</option>)}</select></label></div></section>
    <section className="mt-8" aria-labelledby="song-results-title"><div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b-2 border-foreground pb-3"><div><h2 id="song-results-title" className="scroll-mt-24 font-heading text-2xl font-bold">Results</h2>{songs.isFetching && data && <p role="status" className="mt-1 text-xs text-muted-foreground">Updating results…</p>}</div>{data && <span className="text-sm tabular-nums text-muted-foreground">{data.count} {data.count === 1 ? "song" : "songs"}</span>}</div>
      {songs.isLoading && !data ? <LoadingState label="Loading songs…" /> : songs.isError ? <div role="alert" className="border border-destructive bg-danger-surface p-4"><p className="font-semibold">Songs could not load.</p><button type="button" onClick={() => songs.refetch()} className="mt-3 min-h-10 border-2 border-foreground bg-card px-3 text-sm font-bold">Retry</button></div> : data?.results.length ? <SongResults songs={data.results} empty="No songs match this search." /> : <EmptyState message="No songs match this search." />}
      {data && (data.previous || data.next) && <nav aria-label="Song pages" className="mt-6 flex items-center justify-between gap-4">{data.previous ? <button type="button" onClick={() => paginate(filters.page - 1)} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Previous</button> : <span />}<span className="text-sm font-semibold tabular-nums">Page {filters.page} of {archivePageCount(data.count)}</span>{data.next ? <button type="button" onClick={() => paginate(filters.page + 1)} className="min-h-11 border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Next</button> : <span />}</nav>}
    </section>
  </main>;
}
