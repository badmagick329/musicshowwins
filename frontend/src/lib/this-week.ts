import type { ArchiveWeek, EpisodeStatus, Show, Win } from "@/lib/api-shared";

// Regular broadcast days (ISO weekday, Monday = 1). Specials on other days still
// appear under their show because slots match by show, not by date.
export const BROADCAST_SCHEDULE = [
  { slug: "the-show", weekday: 2 },
  { slug: "show-champion", weekday: 3 },
  { slug: "m-countdown", weekday: 4 },
  { slug: "music-bank", weekday: 5 },
  { slug: "music-core", weekday: 6 },
  { slug: "inkigayo", weekday: 7 },
] as const;

export type WeekSlot = { slug: string; name: string; date: string; status: "won" | "upcoming" | "no-result" | EpisodeStatus["status"]; wins: Win[] };

/** Broadcast weeks follow Korean dates, not the server's timezone. */
export function koreaToday(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

export function addDays(date: string, days: number) {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function weekStart(date: string) {
  const weekday = new Date(`${date}T00:00:00Z`).getUTCDay() || 7;
  return addDays(date, 1 - weekday);
}

/** The current week once it has a result; otherwise the latest week that does, so the section is never empty. */
export function chooseWeek(today: string, currentWins: Win[], latestWins: Win[]): ArchiveWeek {
  const start = weekStart(today);
  if (currentWins.length || !latestWins.length) return { start, end: addDays(start, 6), current: true, wins: currentWins, episodes: [] };
  const latestStart = weekStart(latestWins.reduce((latest, win) => (win.date > latest ? win.date : latest), latestWins[0].date));
  const end = addDays(latestStart, 6);
  return { start: latestStart, end, current: false, wins: latestWins.filter((win) => win.date >= latestStart && win.date <= end), episodes: [] };
}

export function buildWeek(week: ArchiveWeek, shows: Show[], today: string): WeekSlot[] {
  const names = new Map(shows.map((show) => [show.slug, show.name]));
  return BROADCAST_SCHEDULE.filter((entry) => names.has(entry.slug)).map(({ slug, weekday }) => {
    const wins = week.wins.filter((win) => win.show.slug === slug).toSorted((a, b) => a.date.localeCompare(b.date));
    const episode = week.episodes.find((item) => item.show === slug);
    const date = wins[0]?.date ?? episode?.date ?? addDays(week.start, weekday - 1);
    const status = wins.length ? "won" : episode ? episode.status : date >= today ? "upcoming" : "no-result";
    return { slug, name: names.get(slug)!, date, status, wins };
  });
}

// Worded to stay true for every source label the status was classified from.
export const EPISODE_STATUS_TEXT: Record<EpisodeStatus["status"], string> = {
  not_aired: "No broadcast",
  special: "Special episode, no winner",
  no_winner: "No winner announced",
};

export function formatWeekRange(start: string, end: string) {
  const day = (value: string) => new Intl.DateTimeFormat("en-GB", { day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
  const month = (value: string) => new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
  return month(start) === month(end) ? `${day(start)}–${day(end)} ${month(end)}` : `${day(start)} ${month(start)} – ${day(end)} ${month(end)}`;
}

export function formatSlotDay(date: string) {
  return new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${date}T00:00:00Z`));
}
