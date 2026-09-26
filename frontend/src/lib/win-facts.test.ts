import { describe, expect, it } from "vitest";
import type { Win } from "./api-shared";
import { cardFacts, notableTag, ordinal } from "./win-facts";

function win(date: string, milestones: Win["milestones"]): Win {
  return {
    id: 1,
    date,
    show: { id: 1, name: "Inkigayo", slug: "inkigayo", active: true },
    song: { id: 1, title: "Bad", artist: { id: 1, slug: "ateez", name: "Ateez" }, total_wins: 7, winning_shows: 4, latest_win_date: date },
    performed: null, references: [],
    milestones,
  };
}

describe("win facts", () => {
  it("formats English ordinals including the teens", () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111].map(ordinal)).toEqual(["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "101st", "111th"]);
  });

  it("keeps one tag, preferring artist milestones", () => {
    expect(notableTag(win("2024-05-01", { artist_win: 1, song_show_win: 1, song_win: 1 }))).toBe("1st recorded win for Ateez");
    expect(notableTag(win("2024-05-01", { artist_win: 49, song_show_win: 3, song_win: 10 }))).toBe("Triple crown · Inkigayo");
    expect(notableTag(win("2024-05-01", { artist_win: 50, song_show_win: 3, song_win: 10 }))).toBe("50th recorded win for Ateez");
    expect(notableTag(win("2024-05-01", { artist_win: 51, song_show_win: 2, song_win: 10 }))).toBe("10th recorded win for Bad");
    expect(notableTag(win("2024-05-01", { artist_win: 7, song_show_win: 2, song_win: 4 }))).toBeNull();
  });

  it("makes no ordinal claims at the start of catalogue coverage", () => {
    const early = win("2014-02-01", { artist_win: 1, song_show_win: 3, song_win: 3 });
    expect(notableTag(early)).toBeNull();
    expect(cardFacts(early)).toEqual({ count: null, tag: null });
  });

  it("gives cards the song count without repeating a milestone", () => {
    expect(cardFacts(win("2026-09-20", { artist_win: 1, song_show_win: 1, song_win: 1 }))).toEqual({ count: null, tag: "1st recorded win for Ateez" });
    expect(cardFacts(win("2026-09-20", { artist_win: 36, song_show_win: 3, song_win: 7 }))).toEqual({ count: "7th recorded win for Bad", tag: "Triple crown · Inkigayo" });
    expect(cardFacts(win("2026-09-20", { artist_win: 37, song_show_win: 2, song_win: 10 }))).toEqual({ count: "10th recorded win for Bad", tag: null });
  });
});
