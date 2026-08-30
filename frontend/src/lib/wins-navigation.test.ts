import { describe, expect, it } from "vitest";
import { defaultWinsFilters } from "./wins-filters";
import { clearWinsNavigation, winsFiltersFromSearchParams } from "./wins-navigation";

describe("wins URL navigation", () => {
  it("resolves an empty URL to default filters", () => {
    expect(winsFiltersFromSearchParams(new URLSearchParams())).toEqual(defaultWinsFilters());
  });

  it("clears an initially filtered URL to the unfiltered route", () => {
    const current = winsFiltersFromSearchParams(new URLSearchParams("show=music-bank&year=2025"));
    expect(clearWinsNavigation(current)).toMatchObject({ url: "/wins", mode: "push", filters: defaultWinsFilters() });
  });
});
