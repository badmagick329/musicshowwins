import { describe, expect, it } from "vitest";
import type { Win } from "./api-shared";
import { artistHighlights, buildShowBreakdown, summarizeArtist } from "./artist-profile";

function win(id: number, date: string, show: { id: number; slug: string; name: string }, songId: number): Win {
  return { id, date, show: { ...show, active: true }, song: { id: songId, title: `Song ${songId}`, artist: { id: 1, slug: "artist", name: "Artist" }, total_wins: 1, latest_win_date: date, winning_shows: 1 }, performed: null, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 } };
}

const bank = { id: 1, slug: "music-bank", name: "Music Bank" };
const core = { id: 2, slug: "music-core", name: "Music Core" };
const countdown = { id: 3, slug: "m-countdown", name: "M Countdown" };

describe("artist profile calculations", () => {
  const wins = [win(1, "2025-01-02", bank, 10), win(2, "2023-06-01", core, 11), win(3, "2024-04-03", bank, 10), win(4, "2025-02-01", countdown, 12)];

  it("calculates totals, unique winning songs, and date range", () => {
    expect(summarizeArtist(wins)).toEqual({ totalWins: 4, winningSongs: 3, earliestWin: wins[1], latestWin: wins[3] });
    expect(summarizeArtist([])).toEqual({ totalWins: 0, winningSongs: 0, earliestWin: null, latestWin: null });
  });

  it("retains song and show details without changing history order, with stable same-day ties", () => {
    const sameDay = win(5, "2023-06-01", bank, 12);
    const input = [sameDay, ...wins];
    expect(summarizeArtist(input).earliestWin).toBe(wins[1]);
    expect(input).toEqual([sameDay, ...wins]);
  });

  it("sorts show totals by count then show name", () => {
    expect(buildShowBreakdown(wins).map(({ name, wins: count }) => [name, count])).toEqual([["Music Bank", 2], ["M Countdown", 1], ["Music Core", 1]]);
  });

  it("derives highlights and skips ones that only restate the summary", () => {
    expect(artistHighlights(wins)).toEqual(["Most wins: Song 10 (2)", "Best year: 2025 (2 wins)"]);
    const crown = [win(5, "2024-01-01", bank, 10), win(6, "2024-02-01", bank, 10), win(7, "2024-03-01", bank, 10)];
    expect(artistHighlights(crown)).toEqual(["1 triple crown"]);
    const tie = [...crown, win(8, "2025-01-01", core, 11), win(9, "2025-02-01", core, 11), win(10, "2025-03-01", core, 11)];
    expect(artistHighlights(tie)).toEqual(["Most wins: Song 10 and Song 11 (3)", "Best year: 2025 (3 wins)", "2 triple crowns"]);
    const threeWay = [win(11, "2024-01-01", bank, 1), win(12, "2024-01-02", bank, 2), win(13, "2024-01-03", bank, 3)];
    expect(artistHighlights(threeWay)).toEqual([]);
  });
});
