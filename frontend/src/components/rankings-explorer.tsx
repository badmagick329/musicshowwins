"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArchivePageLink } from "@/components/archive-page-link";
import { EmptyState, LoadingState, RankMarker } from "@/components/data-display";
import { ArchiveResultsSummary } from "@/components/pagination";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { browserTransport } from "@/lib/api-browser";
import type { ArtistLeaderboardRow, SongLeaderboardRow } from "@/lib/api-shared";
import { archivePageCount } from "@/lib/pagination";
import { archiveStartYear } from "@/lib/wins-filters";
import { parseRankingSelection, rankingHeading, rankingUrl, rankingWinsUrl, type RankingKind, type RankingSelection } from "@/lib/rankings";
import { rankingsQueryOptions } from "@/lib/rankings-queries";
import { usePaginationScroll } from "@/lib/use-pagination-scroll";

function RankingRows({ rows, selection, today }: { rows: (ArtistLeaderboardRow | SongLeaderboardRow)[]; selection: RankingSelection; today: string }) {
  const details = rows.map((row) => {
    const artist = selection.kind === "artists" ? (row as ArtistLeaderboardRow).artist : (row as SongLeaderboardRow).song.artist;
    const song = selection.kind === "songs" ? (row as SongLeaderboardRow).song : null;
    const name = song?.title ?? artist.name;
    const detailUrl = song ? `/songs/${song.id}` : `/artists/${artist.id}`;
    const winsUrl = rankingWinsUrl(selection, song?.id ?? artist.id, today);
    return { row, artist, song, name, detailUrl, winsUrl };
  });
  return <div className="border border-border bg-card">
    <Table className="desktop-table w-full border-collapse text-sm">
      <TableCaption className="sr-only">{rankingHeading(selection)} by music-show wins</TableCaption>
      <TableHeader><TableRow className="border-b-2 border-foreground bg-muted/50 text-xs uppercase tracking-[0.12em] text-muted-foreground"><TableHead className="w-16 px-4 py-3">Rank</TableHead><TableHead className="px-4 py-3">{selection.kind === "songs" ? "Song and artist" : "Artist"}</TableHead><TableHead className="w-24 px-4 py-3 text-right">Wins</TableHead></TableRow></TableHeader>
      <TableBody>{details.map(({ row, artist, song, name, detailUrl, winsUrl }) => <TableRow key={song?.id ?? artist.id} className="border-border/70 transition-colors hover:bg-accent/60"><TableCell className="w-16 px-4 py-3"><RankMarker rank={row.rank} /></TableCell><TableCell className="px-4 py-3"><Link prefetch={false} href={detailUrl} className="compact-link-target font-semibold">{name}</Link>{song && <p className="text-xs text-muted-foreground"><Link prefetch={false} href={`/artists/${artist.id}`} className="compact-link-target">{artist.name}</Link></p>}</TableCell><TableCell className="w-24 px-4 py-3 text-right font-heading text-lg font-bold tabular-nums"><Link prefetch={false} href={winsUrl} aria-label={`View ${row.wins} wins for ${name} in this period`} className="compact-link-target underline-offset-4 hover:underline">{row.wins}</Link></TableCell></TableRow>)}</TableBody>
    </Table>
    <div className="mobile-record flex-col"><div className="flex items-center justify-between border-b-2 border-foreground bg-muted/50 px-3 py-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground"><span>Rank · {selection.kind === "songs" ? "song" : "artist"}</span><span>Wins</span></div>{details.map(({ row, artist, song, name, detailUrl, winsUrl }) => <div key={song?.id ?? artist.id} className="mobile-record items-center gap-3 border-b border-border/70 px-3 py-3"><RankMarker rank={row.rank} /><div className="min-w-0 flex-1"><p className="break-words font-semibold"><Link prefetch={false} href={detailUrl} className="compact-link-target">{name}</Link></p>{song && <p className="break-words text-xs text-muted-foreground"><Link prefetch={false} href={`/artists/${artist.id}`} className="compact-link-target">{artist.name}</Link></p>}</div><Link prefetch={false} href={winsUrl} aria-label={`View ${row.wins} ${row.wins === 1 ? "win" : "wins"} for ${name} in this period`} className="compact-link-target shrink-0 font-heading text-lg font-bold tabular-nums underline-offset-4 hover:underline">{row.wins}</Link></div>)}</div>
  </div>;
}

export function RankingsExplorer({ today }: { today: string }) {
  const searchParams = useSearchParams();
  const params: Record<string, string> = {};
  searchParams.forEach((value, key) => { params[key] = value; });
  const selection = parseRankingSelection(params, today);
  return <RankingsView selection={selection} today={today} />;
}

function RankingControls({ selection, today, navigate }: { selection: RankingSelection; today: string; navigate: (next: RankingSelection) => void }) {
  const [draftPeriod, setDraftPeriod] = useState<"custom" | null>(null);
  const [dateFrom, setDateFrom] = useState(selection.dateFrom);
  const [dateTo, setDateTo] = useState(selection.dateTo);
  const [formError, setFormError] = useState<string | null>(null);
  const currentYear = Number(today.slice(0, 4));
  const periodValue = draftPeriod ?? (selection.period === "year" ? String(selection.year) : selection.period);
  const years = Array.from({ length: currentYear - archiveStartYear + 1 }, (_, index) => currentYear - index);

  function changePeriod(value: string) {
    setFormError(null);
    if (value === "custom") { setDraftPeriod("custom"); return; }
    setDraftPeriod(null);
    navigate({ ...selection, period: value === "all-time" ? "all-time" : "year", year: value === "all-time" ? currentYear : Number(value), dateFrom: "", dateTo: "" });
  }

  function applyCustom(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidate = parseRankingSelection({ kind: selection.kind, period: "custom", date_from: dateFrom, date_to: dateTo }, today);
    if (candidate.error) { setFormError(candidate.error); return; }
    setFormError(null);
    navigate(candidate);
  }

  return <section aria-label="Ranking controls" className="mt-7 border-2 border-foreground bg-search-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-end gap-4">
        <div role="group" aria-label="Rank songs or artists" className="flex min-h-11 border-2 border-foreground bg-card">
          {(["songs", "artists"] as RankingKind[]).map((kind) => <button key={kind} type="button" aria-pressed={selection.kind === kind} onClick={() => navigate({ ...selection, kind })} className={`min-h-11 px-4 text-sm font-bold ${selection.kind === kind ? "bg-action-pink text-white" : "hover:bg-accent"}`}>{kind === "songs" ? "Songs" : "Artists"}</button>)}
        </div>
        <label className="min-w-[12rem] flex-1 text-sm font-bold sm:max-w-xs">Period
          <select value={periodValue} onChange={(event) => changePeriod(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal">
            <option value={currentYear}>This year ({currentYear})</option>
            {years.slice(1).map((year) => <option key={year} value={year}>{year}</option>)}
            <option value="all-time">All time</option><option value="custom">Custom dates</option>
          </select>
        </label>
      </div>
      {periodValue === "custom" && <form onSubmit={applyCustom} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="min-w-[10rem] flex-1 text-sm font-bold sm:max-w-56">Start date<input type="date" required value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal tabular-nums" /></label>
        <label className="min-w-[10rem] flex-1 text-sm font-bold sm:max-w-56">End date<input type="date" required value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-foreground bg-card px-3 font-normal tabular-nums" /></label>
        <button type="submit" className="min-h-11 border-2 border-foreground bg-highlight-yellow px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Apply</button>
      </form>}
      {(formError || selection.error) && <p role="alert" className="mt-3 border-l-4 border-destructive bg-danger-surface px-3 py-2 text-sm">{formError || selection.error}</p>}
    </section>;
}

function RankingsView({ selection, today }: { selection: RankingSelection; today: string }) {
  const query = useQuery({ ...rankingsQueryOptions(selection, today, browserTransport), enabled: !selection.error, placeholderData: keepPreviousData });
  const data = query.data;
  const resultsSelection = data?.selection ?? selection;
  const { requestPaginationScroll, cancelPaginationScroll } = usePaginationScroll(selection.page, Boolean(data) && !query.isPlaceholderData && !query.isFetching, "rankings-results-title");

  function navigate(next: RankingSelection) {
    cancelPaginationScroll();
    const url = rankingUrl({ ...next, page: 1, error: null }, today);
    if (url !== rankingUrl(selection, today)) window.history.pushState(null, "", url);
  }

  function paginate(page: number) {
    requestPaginationScroll(page);
    window.history.pushState(null, "", rankingUrl({ ...selection, page }, today));
  }

  return <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
    <header className="border-2 border-foreground bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
      <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">Music show rankings</h1>
      <p className="mt-2 max-w-2xl text-surface-berry-foreground/80">Rankings count music-show wins earned during the selected period.</p>
    </header>
    <RankingControls key={rankingUrl(selection, today)} selection={selection} today={today} navigate={navigate} />
    <section aria-labelledby="rankings-results-title" className="mt-8">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b-2 border-foreground pb-3"><div><h2 id="rankings-results-title" className="scroll-mt-24 font-heading text-2xl font-bold">{selection.error ? "Rankings" : rankingHeading(resultsSelection)}</h2>{query.isFetching && data && <p role="status" className="mt-1 text-xs text-muted-foreground">Updating results…</p>}</div>{data && <ArchiveResultsSummary totalCount={data.count} page={resultsSelection.page} resultCount={data.results.length} singular={resultsSelection.kind === "songs" ? "song" : "artist"} plural={resultsSelection.kind} />}</div>
      {selection.error ? null : query.isLoading && !data ? <LoadingState label="Loading rankings…" /> : query.isError ? <div role="alert" className="border border-destructive bg-danger-surface p-4"><p className="font-semibold">Rankings couldn&apos;t load.</p><button type="button" onClick={() => query.refetch()} className="mt-3 min-h-10 border-2 border-foreground bg-card px-3 text-sm font-bold">Try again</button></div> : data?.results.length ? <RankingRows rows={data.results} selection={resultsSelection} today={today} /> : <EmptyState message="No wins were recorded in this period." />}
      {data && !selection.error && !query.isPlaceholderData && (data.previous || data.next) && <nav aria-label="Ranking pages" className="mt-6 flex items-center justify-between gap-4">
        {data.previous ? <ArchivePageLink href={`${rankingUrl({ ...resultsSelection, page: resultsSelection.page - 1 }, today)}#rankings-results-title`} onNavigate={() => paginate(resultsSelection.page - 1)}>Previous</ArchivePageLink> : <span />}
        <span className="text-sm font-semibold tabular-nums">Page {resultsSelection.page} of {archivePageCount(data.count)}</span>
        {data.next ? <ArchivePageLink href={`${rankingUrl({ ...resultsSelection, page: resultsSelection.page + 1 }, today)}#rankings-results-title`} onNavigate={() => paginate(resultsSelection.page + 1)}>Next</ArchivePageLink> : <span />}
      </nav>}
    </section>
  </main>;
}
