import type { Win } from "@/lib/api-shared";

export type ArtistSummary = {
  totalWins: number;
  winningSongs: number;
  firstWin: string | null;
  earliestWin: Win | null;
  latestWin: string | null;
};

export type ShowBreakdown = {
  id: number;
  slug: string;
  name: string;
  wins: number;
};

export function summarizeArtist(wins: Win[]): ArtistSummary {
  const chronological = [...wins].sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id);
  return {
    totalWins: wins.length,
    winningSongs: new Set(wins.map((win) => win.song.id)).size,
    firstWin: chronological[0]?.date ?? null,
    // Catalogue order, moments, and reference checks do not verify a career first.
    earliestWin: chronological[0] ?? null,
    latestWin: chronological.at(-1)?.date ?? null,
  };
}

export function buildShowBreakdown(wins: Win[]): ShowBreakdown[] {
  const shows = new Map<number, ShowBreakdown>();
  for (const win of wins) {
    const current = shows.get(win.show.id);
    if (current) current.wins += 1;
    else shows.set(win.show.id, { id: win.show.id, slug: win.show.slug, name: win.show.name, wins: 1 });
  }
  return [...shows.values()].sort((a, b) => b.wins - a.wins || a.name.localeCompare(b.name));
}
