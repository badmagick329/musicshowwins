import { describe, expect, it } from "vitest";
import type { Show, Win } from "./api-shared";
import { buildWeek, chooseWeek, formatSlotDay, formatWeekRange, koreaToday, weekStart } from "./this-week";

const shows: Show[] = [
  ["the-show", "The Show"], ["show-champion", "Show Champion"], ["m-countdown", "M Countdown"],
  ["music-bank", "Music Bank"], ["music-core", "Show! Music Core"], ["inkigayo", "Inkigayo"],
].map(([slug, name], index) => ({ id: index + 1, slug, name, active: true, total_wins: 0 }) as unknown as Show);

function win(id: number, date: string, slug: string): Win {
  const show = shows.find((item) => item.slug === slug)!;
  return { id, date, show: { id: show.id, slug, name: show.name, active: true }, song: { id, title: `Song ${id}`, artist: { id: 1, name: "Artist" }, total_wins: 1, winning_shows: 1, latest_win_date: date }, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 } };
}

describe("this week", () => {
  it("uses the Korean date, which is ahead of UTC", () => {
    // 15:30 UTC Sunday is 00:30 Monday in Seoul, the start of a new broadcast week.
    expect(koreaToday(new Date("2026-09-27T15:30:00Z"))).toBe("2026-09-28");
    expect(weekStart("2026-09-28")).toBe("2026-09-28");
    expect(weekStart("2026-09-27")).toBe("2026-09-21");
  });

  it("marks won, past and upcoming slots in broadcast order", () => {
    const week = chooseWeek("2026-09-24", [win(1, "2026-09-22", "the-show")], []);
    expect(week).toMatchObject({ start: "2026-09-21", end: "2026-09-27", current: true });
    const slots = buildWeek(week, shows, "2026-09-24");
    expect(slots.map((slot) => [slot.slug, slot.date, slot.status])).toEqual([
      ["the-show", "2026-09-22", "won"],
      ["show-champion", "2026-09-23", "no-result"],
      ["m-countdown", "2026-09-24", "upcoming"],
      ["music-bank", "2026-09-25", "upcoming"],
      ["music-core", "2026-09-26", "upcoming"],
      ["inkigayo", "2026-09-27", "upcoming"],
    ]);
  });

  it("falls back to the latest week with results instead of an empty section", () => {
    const latest = [win(3, "2026-09-20", "inkigayo"), win(2, "2026-09-19", "music-core"), win(1, "2026-09-12", "music-core")];
    const week = chooseWeek("2026-09-25", [], latest);
    expect(week).toMatchObject({ start: "2026-09-14", end: "2026-09-20", current: false });
    expect(week.wins.map((item) => item.id)).toEqual([3, 2]);
    expect(buildWeek(week, shows, "2026-09-25").filter((slot) => slot.status === "won").map((slot) => slot.slug)).toEqual(["music-core", "inkigayo"]);
  });

  it("formats compact ranges and slot days", () => {
    expect(formatWeekRange("2026-09-21", "2026-09-27")).toBe("21–27 Sept");
    expect(formatWeekRange("2026-09-28", "2026-10-04")).toBe("28 Sept – 4 Oct");
    expect(formatSlotDay("2026-09-27")).toBe("Sun 27 Sept");
  });
});
