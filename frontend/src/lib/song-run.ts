import type { Win } from "@/lib/api-shared";
import { weekStart } from "@/lib/this-week";

// The six tracked shows in broadcast-week order, named as the API names them.
const TRACKED_SHOWS = [
  { slug: "the-show", name: "The Show" },
  { slug: "show-champion", name: "Show Champion" },
  { slug: "m-countdown", name: "M Countdown" },
  { slug: "music-bank", name: "Music Bank" },
  { slug: "music-core", name: "Show! Music Core" },
  { slug: "inkigayo", name: "Inkigayo" },
];
// Music Core had no chart between these dates, so it could not be won.
const MUSIC_CORE_GAP = { from: "2015-11-15", to: "2017-04-21" };
// A run starting this early may have begun in 2013, before coverage.
const COVERAGE_SAFE_FROM = "2014-03-01";
const SWEEP_MIN_SHOWS = 3;

const MONTH = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });
const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", timeZone: "UTC" });
const parts = (date: string) => {
  const value = new Date(`${date}T00:00:00Z`);
  return { day: DAY.format(value), month: MONTH.format(value), year: date.slice(0, 4) };
};

function formatDateRange(start: string, end: string) {
  const [a, b] = [parts(start), parts(end)];
  if (start === end) return `${a.day} ${a.month} ${a.year}`;
  if (a.year !== b.year) return `${a.day} ${a.month} ${a.year} – ${b.day} ${b.month} ${b.year}`;
  if (a.month !== b.month) return `${a.day} ${a.month} – ${b.day} ${b.month} ${b.year}`;
  return `${a.day}–${b.day} ${b.month} ${b.year}`;
}

function between(start: string, end: string) {
  const [a, b] = [parts(start), parts(end)];
  const from = a.year === b.year ? `${a.day} ${a.month}` : `${a.day} ${a.month} ${a.year}`;
  return `between ${from} and ${b.day} ${b.month} ${b.year}`;
}

function listNames(names: string[]) {
  return names.length < 3 ? names.join(" and ") : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
}

/** The Korean calendar week (Mon–Sun, same rule as This week) in which the song won the most different shows. */
function bestWeek(wins: Win[]) {
  const weeks = new Map<string, Win[]>();
  for (const win of wins) {
    const start = weekStart(win.date);
    weeks.set(start, [...(weeks.get(start) ?? []), win]);
  }
  let best: { shows: number; wins: Win[] } | null = null;
  for (const [, weekWins] of [...weeks].sort(([a], [b]) => a.localeCompare(b))) {
    const shows = new Set(weekWins.map((win) => win.show.slug)).size;
    if (!best || shows > best.shows) best = { shows, wins: weekWins };
  }
  return best!;
}

/**
 * One line answering "did X win, where, and how big was the run?", which song-page
 * searches ask and a winner list only answers row by row. Stays silent when the run
 * could have started before coverage, rather than understating it.
 */
export function songRunSummary(wins: Win[]): string | null {
  if (!wins.length) return null;
  const sorted = wins.toSorted((a, b) => a.date.localeCompare(b.date));
  const [first, last] = [sorted[0].date, sorted.at(-1)!.date];
  if (first < COVERAGE_SAFE_FROM) return null;

  const won = new Set(sorted.map((win) => win.show.slug));
  const coreDark = first >= MUSIC_CORE_GAP.from && last <= MUSIC_CORE_GAP.to;
  const available = TRACKED_SHOWS.filter((show) => !(coreDark && show.slug === "music-core"));
  const missed = available.filter((show) => !won.has(show.slug)).map((show) => show.name);
  const wonNames = TRACKED_SHOWS.filter((show) => won.has(show.slug)).map((show) => show.name);

  if (sorted.length === 1) return `Won once, on ${wonNames[0]} (${formatDateRange(first, first)}).`;

  const total = available.length === 6 ? "six" : "five";
  const shows = !missed.length
    ? `Won on all ${total} shows${coreDark ? " charting at the time" : ""}`
    : won.size >= 4
      ? `Won on ${won.size} of ${available.length} shows (all but ${listNames(missed)})`
      : `Won on ${listNames(wonNames)}`;

  const week = bestWeek(sorted);
  const weekRange = formatDateRange(week.wins[0].date, week.wins.at(-1)!.date);
  if (week.wins.length === sorted.length && week.shows >= 2) return `${shows}, all in one week (${weekRange}).`;
  const span = between(first, last);
  const sweep = week.shows >= SWEEP_MIN_SHOWS ? `, including ${week.shows} shows in one week (${weekRange})` : "";
  return `${shows} ${span}${sweep}.`;
}
