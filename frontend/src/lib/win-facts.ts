import type { Win } from "@/lib/api-shared";

// The catalogue starts in 2014, so ordinals for that year may omit earlier wins.
const COVERAGE_START_YEAR = "2014";
const ARTIST_MILESTONES = new Set([10, 25, 50, 100, 150, 200]);
const SONG_MILESTONES = new Set([10, 20, 30]);

export function ordinal(value: number) {
  const tens = value % 100;
  if (tens >= 11 && tens <= 13) return `${value}th`;
  return `${value}${({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[value % 10] ?? "th"}`;
}

/**
 * At most one label for the few wins worth calling out in long histories.
 * Wording says "recorded" because the catalogue cannot establish a career first.
 */
export function notableTag(win: Win): string | null {
  const { artist_win, song_show_win, song_win } = win.milestones;
  if (win.date.startsWith(COVERAGE_START_YEAR)) return null;
  if (artist_win === 1 || ARTIST_MILESTONES.has(artist_win)) return `${ordinal(artist_win)} recorded win for ${win.song.artist.name}`;
  if (song_show_win === 3) return `Triple crown · ${win.show.name}`;
  if (SONG_MILESTONES.has(song_win)) return `${ordinal(song_win)} recorded win for ${win.song.title}`;
  return null;
}

/**
 * A This week card shows the song's running count plus any other notable tag.
 * An artist's first recorded win implies the song's, so only the tag remains.
 */
export function cardFacts(win: Win): { count: string | null; tag: string | null } {
  if (win.date.startsWith(COVERAGE_START_YEAR)) return { count: null, tag: null };
  const tag = notableTag(win);
  const count = `${ordinal(win.milestones.song_win)} recorded win for ${win.song.title}`;
  if (win.milestones.artist_win === 1) return { count: null, tag };
  return { count, tag: tag === count ? null : tag };
}
