import Link from "next/link";
import { artistsUrl, type ArtistSort } from "@/lib/artist-list";
import { archivePageCount, archivePageSize } from "@/lib/pagination";

export function ArchiveResultsSummary({ totalCount, page, resultCount, singular, plural }: { totalCount: number; page: number; resultCount: number; singular: string; plural: string }) {
  const label = totalCount === 1 ? singular : plural;
  if (!totalCount) return <span className="text-sm tabular-nums text-muted-foreground">0 {plural}</span>;
  const from = (page - 1) * archivePageSize + 1;
  const to = from + resultCount - 1;
  return <span aria-live="polite" className="text-sm tabular-nums text-muted-foreground">{from}–{to} of {totalCount} {label} · Page {page} of {archivePageCount(totalCount)}</span>;
}

export function Pagination({ page, totalCount, hasPrevious, hasNext, search = "", sort }: { page: number; totalCount: number; hasPrevious: boolean; hasNext: boolean; search?: string; sort: ArtistSort }) {
  if (!hasPrevious && !hasNext) return null;
  const linkClass = "inline-flex min-h-11 items-center border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5";
  const pageHref = (targetPage: number) => `${artistsUrl({ page: targetPage, search, sort })}#artist-results-title`;
  return (
    <nav aria-label="Artist pages" className="mt-6 flex items-center justify-between gap-4">
      {hasPrevious ? <Link className={linkClass} href={pageHref(page - 1)}>Previous</Link> : <span />}
      <span className="text-sm font-semibold tabular-nums">Page {page} of {archivePageCount(totalCount)}</span>
      {hasNext ? <Link className={linkClass} href={pageHref(page + 1)}>Next</Link> : <span />}
    </nav>
  );
}
