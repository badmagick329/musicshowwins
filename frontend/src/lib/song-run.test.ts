import { describe, expect, it } from "vitest";
import type { Win } from "./api-shared";
import { songRunSummary } from "./song-run";

const SHOWS: Record<string, string> = {
  "the-show": "The Show", "show-champion": "Show Champion", "m-countdown": "M Countdown",
  "music-bank": "Music Bank", "music-core": "Show! Music Core", inkigayo: "Inkigayo",
};

let id = 0;
function win(date: string, slug: string): Win {
  id += 1;
  return {
    id, date,
    show: { id: Object.keys(SHOWS).indexOf(slug) + 1, slug, name: SHOWS[slug], active: true },
    song: { id: 1, title: "Boom Boom Bass", artist: { id: 1, slug: "riize", name: "Riize" }, total_wins: 5, winning_shows: 5, latest_win_date: date },
    performed: null, references: [], milestones: { artist_win: 1, song_show_win: 1, song_win: 1 },
  };
}

describe("song run summary", () => {
  it("names the missing shows and a run inside one Korean week", () => {
    const run = [win("2024-06-25", "the-show"), win("2024-06-26", "show-champion"), win("2024-06-27", "m-countdown"), win("2024-06-28", "music-bank"), win("2024-06-30", "inkigayo")];
    expect(songRunSummary(run)).toBe("Won on 5 of 6 shows (all but Show! Music Core), all in one week (25–30 Jun 2024).");
  });

  it("gives the span and the biggest weekly sweep for longer runs", () => {
    const run = [
      win("2021-01-19", "the-show"), win("2021-01-20", "show-champion"), win("2021-01-21", "m-countdown"), win("2021-01-22", "music-bank"), win("2021-01-23", "music-core"), win("2021-01-24", "inkigayo"),
      win("2021-01-31", "inkigayo"), win("2021-02-05", "music-bank"),
    ];
    expect(songRunSummary(run)).toBe("Won on all six shows between 19 Jan and 5 Feb 2021, including 6 shows in one week (19–24 Jan 2021).");
  });

  it("lists the shows for small runs and skips weak weekly sweeps", () => {
    expect(songRunSummary([win("2023-12-30", "music-core"), win("2024-01-07", "inkigayo")])).toBe("Won on Show! Music Core and Inkigayo between 30 Dec 2023 and 7 Jan 2024.");
    expect(songRunSummary([win("2024-01-18", "m-countdown")])).toBe("Won once, on M Countdown (18 Jan 2024).");
  });

  it("drops Music Core from the count while it had no chart", () => {
    const run = [win("2016-05-03", "the-show"), win("2016-05-04", "show-champion"), win("2016-05-05", "m-countdown"), win("2016-05-06", "music-bank"), win("2016-05-08", "inkigayo")];
    expect(songRunSummary(run)).toBe("Won on all five shows charting at the time, all in one week (3–8 May 2016).");
  });

  it("says nothing when the run may have started before coverage", () => {
    expect(songRunSummary([win("2014-01-05", "inkigayo"), win("2014-01-10", "music-bank")])).toBeNull();
    expect(songRunSummary([])).toBeNull();
  });
});
