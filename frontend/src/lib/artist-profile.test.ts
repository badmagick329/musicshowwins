import { describe, expect, it } from "vitest";
import type { Win } from "./api";
import { buildShowBreakdown, summarizeArtist } from "./artist-profile";

function win(id: number, date: string, show: { id: number; slug: string; name: string }, songId: number): Win {
  return { id, date, show: { ...show, active: true }, song: { id: songId, title: `Song ${songId}`, artist: { id: 1, name: "Artist" }, total_wins: 1 } };
}

const bank = { id: 1, slug: "music-bank", name: "Music Bank" };
const core = { id: 2, slug: "music-core", name: "Music Core" };
const countdown = { id: 3, slug: "m-countdown", name: "M Countdown" };

describe("artist profile calculations", () => {
  const wins = [win(1, "2025-01-02", bank, 10), win(2, "2023-06-01", core, 11), win(3, "2024-04-03", bank, 10), win(4, "2025-02-01", countdown, 12)];

  it("calculates totals, unique winning songs, and date range", () => {
    expect(summarizeArtist(wins)).toEqual({ totalWins: 4, winningSongs: 3, firstWin: "2023-06-01", latestWin: "2025-02-01" });
    expect(summarizeArtist([])).toEqual({ totalWins: 0, winningSongs: 0, firstWin: null, latestWin: null });
  });

  it("sorts show totals by count then show name", () => {
    expect(buildShowBreakdown(wins).map(({ name, wins: count }) => [name, count])).toEqual([["Music Bank", 2], ["M Countdown", 1], ["Music Core", 1]]);
  });
});
