import Link from "next/link";
import { artistsUrl, type ArtistSort } from "@/lib/artist-list";

export function Pagination({ page, hasPrevious, hasNext, search = "", sort }: { page: number; hasPrevious: boolean; hasNext: boolean; search?: string; sort: ArtistSort }) {
  if (!hasPrevious && !hasNext) return null;
  const linkClass = "inline-flex min-h-11 items-center border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5";
  return (
    <nav aria-label="Artist pages" className="mt-6 flex items-center justify-between gap-4">
      {hasPrevious ? <Link className={linkClass} href={artistsUrl({ page: page - 1, search, sort })}>Previous</Link> : <span />}
      <span className="text-sm font-semibold tabular-nums">Page {page}</span>
      {hasNext ? <Link className={linkClass} href={artistsUrl({ page: page + 1, search, sort })}>Next</Link> : <span />}
    </nav>
  );
}
