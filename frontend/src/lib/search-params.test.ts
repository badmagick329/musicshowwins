import { describe, expect, it } from "vitest";
import { buildSearchUrl, normalizeSearchQuery } from "./search-params";

describe("debounced search parameters", () => {
  it("trims the applied query", () => {
    expect(normalizeSearchQuery("  bts  ")).toBe("bts");
  });

  it("preserves sort and resets the artist page", () => {
    expect(buildSearchUrl("/artists", "sort=name-desc&page=4&search=old", " bts ")).toBe("/artists?sort=name-desc&search=bts");
  });

  it("updates homepage search without changing its path", () => {
    expect(buildSearchUrl("/", "search=old", "aespa")).toBe("/?search=aespa");
  });

  it("removes empty search values", () => {
    expect(buildSearchUrl("/artists", "sort=wins&page=2&search=bts", "   ")).toBe("/artists?sort=wins");
  });
});
