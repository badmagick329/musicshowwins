import { describe, expect, it } from "vitest";
import { artistOrderings, artistsUrl, parseArtistSort } from "./artist-list";

describe("artist list parameters", () => {
  it("falls back to most wins for missing and invalid sorts", () => {
    expect(parseArtistSort(undefined)).toBe("wins");
    expect(parseArtistSort("invalid")).toBe("wins");
    expect(parseArtistSort(["name"])).toBe("wins");
  });

  it("supports every sort mapping", () => {
    expect(artistOrderings).toEqual({ wins: "-total_wins,name", name: "name", "name-desc": "-name" });
  });

  it("preserves search and sort through pagination", () => {
    expect(artistsUrl({ search: "  bts  ", sort: "name-desc", page: 3 })).toBe("/artists?sort=name-desc&search=bts&page=3");
  });

  it("resets pagination when a sort link is built", () => {
    expect(artistsUrl({ search: "bts", sort: "name" })).toBe("/artists?sort=name&search=bts");
  });
});
