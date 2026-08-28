import type { Win } from "@/lib/api";

export type ArtistSummary = {
  totalWins: number;
  winningSongs: number;
  firstWin: string | null;
  latestWin: string | null;
};

export type ShowBreakdown = {
  id: number;
  slug: string;
  name: string;
  wins: number;
};

export function summarizeArtist(wins: Win[]): ArtistSummary {
  const dates = wins.map((win) => win.date).sort();
  return {
    totalWins: wins.length,
    winningSongs: new Set(wins.map((win) => win.song.id)).size,
    firstWin: dates[0] ?? null,
    latestWin: dates.at(-1) ?? null,
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
