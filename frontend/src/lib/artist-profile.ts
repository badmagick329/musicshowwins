import type { ArtistDetail, Win } from "@/lib/api-shared";
import { formatDate } from "@/lib/utils";

// Catalogue coverage starts here; wins before it are not recorded.
const RECORD_START_YEAR = 2014;
const MONTH = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });

export type DebutFact =
  | { kind: "first-win"; sentence: string }
  | { kind: "before-record"; sentence: string };

function possessive(name: string) {
  return name.endsWith("s") ? `${name}'` : `${name}'s`;
}

function formatDebut(debut: string) {
  if (debut.length === 10) return `on ${formatDate(debut)}`;
  if (debut.length === 7) return `in ${MONTH.format(new Date(`${debut}-01T00:00:00Z`))}`;
  return `in ${debut}`;
}

function timeBetween(from: string, to: string) {
  const [start, end] = [new Date(`${from}T00:00:00Z`), new Date(`${to}T00:00:00Z`)];
  const days = Math.round((end.getTime() - start.getTime()) / 86_400_000);
  if (days < 60) return `${days} ${days === 1 ? "day" : "days"}`;
  const months = (end.getUTCFullYear() - start.getUTCFullYear()) * 12 + end.getUTCMonth() - start.getUTCMonth() - (end.getUTCDate() < start.getUTCDate() ? 1 : 0);
  if (months < 24) return `${months} months`;
  return `over ${Math.floor(months / 12)} years`;
}

/**
 * Answers "when was X's first music show win?", which search data shows people ask.
 * The earliest recorded win is only the career first when the act debuted after
 * coverage began; earlier debuts get an explanation instead, and acts without a
 * reviewed debut get nothing, so a first recorded win is never passed off as a first.
 */
export function debutFact(artist: Pick<ArtistDetail, "name" | "debut" | "debut_solo">, earliestWin: Win | null): DebutFact | null {
  const { name, debut, debut_solo: solo } = artist;
  if (!debut) return null;
  const noun = solo ? "solo debut" : "debut";
  if (Number(debut.slice(0, 4)) < RECORD_START_YEAR) {
    const debuted = solo ? "made their solo debut" : "debuted";
    return { kind: "before-record", sentence: `${name} ${debuted} in ${debut.slice(0, 4)}, before this record begins in ${RECORD_START_YEAR}, so any earlier wins are not listed.` };
  }
  if (!earliestWin) return null;
  const when = debut.length === 10 ? `, ${timeBetween(debut, earliestWin.date)} after their ${noun} ${formatDebut(debut)}` : `, after their ${noun} ${formatDebut(debut)}`;
  return {
    kind: "first-win",
    sentence: `${possessive(name)} first win on the six major music shows was “${earliestWin.song.title}” on ${earliestWin.show.name}, ${formatDate(earliestWin.date)}${when}.`,
  };
}

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
 * Up to two derived facts that give every artist page some context beyond totals,
 * without the manual research that notable moments need. Items that would only
 * restate the summary (one song, one year) are skipped.
 */
export function artistHighlights(wins: Win[]): string[] {
  const highlights: string[] = [];
  const songs = new Map<number, { title: string; wins: number }>();
  const years = new Map<string, number>();
  for (const win of wins) {
    const song = songs.get(win.song.id) ?? { title: win.song.title, wins: 0 };
    song.wins += 1;
    songs.set(win.song.id, song);
    if (win.date) years.set(win.date.slice(0, 4), (years.get(win.date.slice(0, 4)) ?? 0) + 1);
  }

  const topWins = Math.max(0, ...[...songs.values()].map((song) => song.wins));
  const leaders = [...songs.values()].filter((song) => song.wins === topWins).map((song) => song.title).sort((a, b) => a.localeCompare(b));
  if (songs.size > 1 && leaders.length <= 2) highlights.push(`Most wins: ${leaders.join(" and ")} (${topWins})`);

  if (years.size > 1) {
    const [year, count] = [...years].sort(([a, x], [b, y]) => y - x || b.localeCompare(a))[0];
    highlights.push(`Best year: ${year} (${count} ${count === 1 ? "win" : "wins"})`);
  }

  return highlights;
}

export type TripleCrown = { song: { id: number; title: string }; shows: string[] };

/**
 * Triple crowns named by song, because fans look them up by song ("exo crown wins")
 * and a bare count answers nothing. Songs are ordered by their first crown and shows
 * by when each was crowned, so the list reads as the artist's history.
 */
export function tripleCrowns(wins: Win[]): TripleCrown[] {
  const counts = new Map<string, number>();
  const crowns = new Map<number, TripleCrown>();
  for (const win of wins.toSorted((a, b) => a.date.localeCompare(b.date))) {
    const key = `${win.song.id}:${win.show.id}`;
    const count = (counts.get(key) ?? 0) + 1;
    counts.set(key, count);
    if (count !== 3) continue;
    const crown = crowns.get(win.song.id) ?? { song: { id: win.song.id, title: win.song.title }, shows: [] };
    crown.shows.push(win.show.name);
    crowns.set(win.song.id, crown);
  }
  return [...crowns.values()];
}
