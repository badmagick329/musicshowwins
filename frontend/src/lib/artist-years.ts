import type { Win } from "@/lib/api-shared";

export function parseArtistYear(value: string | string[] | undefined): string | null {
  return typeof value === "string" && /^[1-9]\d{3}$/.test(value) ? value : null;
}

// Only dated records contribute to period counts; aggregate history has no year.
export function datedArtistWins(wins: Win[]) {
  return wins.filter((win) => /^\d{4}-\d{2}-\d{2}$/.test(win.date));
}

export function artistYears(wins: Win[]) {
  const counts = new Map<number, number>();
  for (const win of datedArtistWins(wins)) {
    const year = Number(win.date.slice(0, 4));
    counts.set(year, (counts.get(year) ?? 0) + 1);
  }
  if (!counts.size) return [];
  const first = Math.min(...counts.keys());
  const last = Math.max(...counts.keys());
  return Array.from({ length: last - first + 1 }, (_, index) => ({ year: String(first + index), count: counts.get(first + index) ?? 0 }));
}
