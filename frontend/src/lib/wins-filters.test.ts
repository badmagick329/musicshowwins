import { describe, expect, it } from "vitest";
import {
  archiveStartYear,
  archiveYears,
  defaultWinsFilters,
  parseWinsFilters,
  serializeWinsFilters,
  updateWinsFilters,
  winsDateRangeError,
} from "./wins-filters";

const now = new Date("2026-08-30T00:00:00Z");

describe("wins filters", () => {
  it("uses safe defaults", () => {
    expect(defaultWinsFilters()).toEqual({ search: "", show: "", year: undefined, dateFrom: "", dateTo: "", ordering: "-date", page: 1 });
    expect(parseWinsFilters({}, now)).toEqual(defaultWinsFilters());
  });

  it("parses every supported URL parameter", () => {
    expect(parseWinsFilters({ search: "  ive ", show: "music-bank", year: "2025", date_from: "2025-01-01", date_to: "2025-02-01", ordering: "date", page: "3" }, now)).toEqual({ search: "ive", show: "music-bank", year: 2025, dateFrom: "2025-01-01", dateTo: "2025-02-01", ordering: "date", page: 3 });
  });

  it("drops invalid year, page, dates, and ordering values", () => {
    expect(parseWinsFilters({ year: "2000", page: "0", date_from: "2025-02-30", date_to: "nope", ordering: "title" }, now)).toEqual(defaultWinsFilters());
  });

  it("serializes only active filters", () => {
    expect(serializeWinsFilters(defaultWinsFilters()).toString()).toBe("");
    expect(serializeWinsFilters({ ...defaultWinsFilters(), search: "bts", show: "music-bank", year: 2025, dateFrom: "2025-01-01", dateTo: "2025-01-02", ordering: "date", page: 2 }).toString()).toBe("search=bts&show=music-bank&year=2025&date_from=2025-01-01&date_to=2025-01-02&ordering=date&page=2");
  });

  it("resets pages for filter changes but not pagination", () => {
    const current = { ...defaultWinsFilters(), page: 4, search: "old" };
    expect(updateWinsFilters(current, { search: "new" }).page).toBe(1);
    expect(updateWinsFilters(current, { page: 5 }).page).toBe(5);
  });

  it("flags invalid date ranges before requests", () => {
    expect(winsDateRangeError({ ...defaultWinsFilters(), dateFrom: "2025-02-02", dateTo: "2025-02-01" })).toMatch(/Start date/);
  });

  it("generates newest-first years from the archive start", () => {
    expect(archiveYears(now)[0]).toBe(2026);
    expect(archiveYears(now).at(-1)).toBe(archiveStartYear);
  });
});
