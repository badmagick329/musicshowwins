import type { Win } from "@/lib/api-shared";

export type ArtistSummary = {
  totalWins: number;
  winningSongs: number;
  earliestWin: Win | null;
  latestWin: Win | null;
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
    // Catalogue order, moments, and reference checks do not verify a career first.
    earliestWin: chronological[0] ?? null,
    latestWin: chronological.at(-1) ?? null,
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

/**
 * Up to three derived facts that give every artist page some context beyond totals,
 * without the manual research that notable moments need. Items that would only
 * restate the summary (one song, one year) are skipped.
 */
export function artistHighlights(wins: Win[]): string[] {
  const highlights: string[] = [];
  const songs = new Map<number, { title: string; wins: number }>();
  const years = new Map<string, number>();
  const songShows = new Map<string, number>();
  for (const win of wins) {
    const song = songs.get(win.song.id) ?? { title: win.song.title, wins: 0 };
    song.wins += 1;
    songs.set(win.song.id, song);
    if (win.date) years.set(win.date.slice(0, 4), (years.get(win.date.slice(0, 4)) ?? 0) + 1);
    const key = `${win.song.id}:${win.show.id}`;
    songShows.set(key, (songShows.get(key) ?? 0) + 1);
  }

  const topWins = Math.max(0, ...[...songs.values()].map((song) => song.wins));
  const leaders = [...songs.values()].filter((song) => song.wins === topWins).map((song) => song.title).sort((a, b) => a.localeCompare(b));
  if (songs.size > 1 && leaders.length <= 2) highlights.push(`Most wins: ${leaders.join(" and ")} (${topWins})`);

  if (years.size > 1) {
    const [year, count] = [...years].sort(([a, x], [b, y]) => y - x || b.localeCompare(a))[0];
    highlights.push(`Best year: ${year} (${count} ${count === 1 ? "win" : "wins"})`);
  }

  const crowns = [...songShows.values()].filter((count) => count >= 3).length;
  if (crowns) highlights.push(`${crowns} triple ${crowns === 1 ? "crown" : "crowns"}`);
  return highlights;
}
