import { describe, expect, it } from "vitest";
import { parseRankingSelection, rankingApiParams, rankingHeading, rankingUrl, rankingWinsUrl } from "./rankings";

const today = "2026-09-14";

describe("ranking periods and links", () => {
  it("defaults to current-year songs and stops current-year counts today", () => {
    const selection = parseRankingSelection({}, today);
    expect(selection).toMatchObject({ kind: "songs", period: "year", year: 2026, page: 1, error: null });
    expect(rankingApiParams(selection, today)).toEqual({ date_from: "2026-01-01", date_to: today, page: 1 });
    expect(rankingHeading(selection)).toBe("Top songs of 2026");
  });

  it("preserves previous-year, all-time, and custom periods through kind and page links", () => {
    const year = parseRankingSelection({ kind: "artists", year: "2025", page: "2" }, today);
    expect(rankingApiParams(year, today)).toEqual({ date_from: "2025-01-01", date_to: "2025-12-31", page: 2 });
    expect(rankingUrl(year, today)).toBe("/rankings?kind=artists&year=2025&page=2");
    expect(rankingUrl({ ...year, kind: "songs", page: 1 }, today)).toBe("/rankings?year=2025");

    const allTime = parseRankingSelection({ kind: "artists", period: "all-time" }, today);
    expect(rankingApiParams(allTime, today)).toEqual({ page: 1 });
    expect(rankingUrl(allTime, today)).toBe("/rankings?kind=artists&period=all-time");
    expect(rankingWinsUrl(allTime, 7)).toBe("/wins?artist=7#wins-results-title");

    const custom = parseRankingSelection({ period: "custom", date_from: "2025-12-31", date_to: "2026-01-01", page: "3" }, today);
    expect(custom.error).toBeNull();
    expect(rankingUrl(custom, today)).toBe("/rankings?period=custom&date_from=2025-12-31&date_to=2026-01-01&page=3");
    expect(rankingWinsUrl(custom, 9)).toBe("/wins?song=9&date_from=2025-12-31&date_to=2026-01-01#wins-results-title");
  });

  it("rejects malformed or competing periods without widening results", () => {
    for (const params of [
      { period: "custom", date_from: "2025-02-30", date_to: "2025-03-01" },
      { period: "custom", date_from: "2025-03-02", date_to: "2025-03-01" },
      { year: "2025", date_from: "2025-01-01" },
      { period: "all-time", year: "2025" },
      { year: "not-a-year" },
    ]) expect(parseRankingSelection(params, today).error).toBeTruthy();
  });
});
