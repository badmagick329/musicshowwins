import { describe, expect, it } from "vitest";
import type { Win } from "./api-shared";
import { artistHighlights, buildShowBreakdown, debutFact, summarizeArtist, tripleCrowns } from "./artist-profile";

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
    expect(artistHighlights(crown)).toEqual([]);
    const tie = [...crown, win(8, "2025-01-01", core, 11), win(9, "2025-02-01", core, 11), win(10, "2025-03-01", core, 11)];
    expect(artistHighlights(tie)).toEqual(["Most wins: Song 10 and Song 11 (3)", "Best year: 2025 (3 wins)"]);
    const threeWay = [win(11, "2024-01-01", bank, 1), win(12, "2024-01-02", bank, 2), win(13, "2024-01-03", bank, 3)];
    expect(artistHighlights(threeWay)).toEqual([]);
  });

  it("names triple crowns by song, in the order they were won", () => {
    const history = [
      win(1, "2024-03-01", core, 20), win(2, "2024-01-01", bank, 10), win(3, "2024-01-08", bank, 10), win(4, "2024-01-15", bank, 10),
      win(5, "2024-01-20", core, 20), win(6, "2024-02-01", core, 20), win(7, "2024-01-10", countdown, 10), win(8, "2024-01-17", countdown, 10),
      win(9, "2024-01-24", countdown, 10), win(10, "2024-02-02", countdown, 10), win(11, "2024-02-03", countdown, 30),
    ];
    expect(tripleCrowns(history)).toEqual([
      { song: { id: 10, title: "Song 10" }, shows: ["Music Bank", "M Countdown"] },
      { song: { id: 20, title: "Song 20" }, shows: ["Music Core"] },
    ]);
    expect(tripleCrowns(history.slice(0, 3))).toEqual([]);
  });

  describe("debut fact", () => {
    const first = { ...win(20, "2024-01-18", countdown, 30), song: { ...win(20, "2024-01-18", countdown, 30).song, title: "Love 119" } };

    it("calls the earliest win a first win only for debuts after coverage began", () => {
      expect(debutFact({ name: "Riize", debut_solo: false, debut: "2023-09-04" }, first)).toEqual({
        kind: "first-win",
        sentence: "Riize's first win on the six major music shows was “Love 119” on M Countdown, 18 Jan 2024, 4 months after their debut on 04 Sept 2023.",
      });
      expect(debutFact({ name: "Stray Kids", debut_solo: false, debut: "2014" }, first)?.sentence).toBe("Stray Kids' first win on the six major music shows was “Love 119” on M Countdown, 18 Jan 2024, after their debut in 2014.");
      expect(debutFact({ name: "Ive", debut_solo: false, debut: "2023-12" }, first)?.sentence).toContain("after their debut in December 2023.");
    });

    it("measures short and long gaps in days and years", () => {
      expect(debutFact({ name: "Ive", debut_solo: false, debut: "2023-12-01" }, first)?.sentence).toContain("48 days after their debut");
      expect(debutFact({ name: "Ive", debut_solo: false, debut: "2021-01-19" }, first)?.sentence).toContain("over 2 years after their debut");
    });

    it("names solo debuts so a member's group debut is not implied", () => {
      expect(debutFact({ name: "Jennie", debut_solo: true, debut: "2018-11-12" }, first)?.sentence).toContain("after their solo debut on 12 Nov 2018.");
      expect(debutFact({ name: "Taeyang", debut_solo: true, debut: "2008" }, first)?.sentence).toBe("Taeyang made their solo debut in 2008, before this record begins in 2014, so any earlier wins are not listed.");
    });

    it("explains pre-coverage debuts and says nothing without a reviewed debut", () => {
      expect(debutFact({ name: "Exo", debut_solo: false, debut: "2012" }, first)).toEqual({ kind: "before-record", sentence: "Exo debuted in 2012, before this record begins in 2014, so any earlier wins are not listed." });
      expect(debutFact({ name: "Exo", debut_solo: false, debut: "2013-12-31" }, first)?.kind).toBe("before-record");
      expect(debutFact({ name: "Collab", debut_solo: false, debut: "" }, first)).toBeNull();
      expect(debutFact({ name: "Riize", debut_solo: false, debut: "2023" }, null)).toBeNull();
    });
  });
});
