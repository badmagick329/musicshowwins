import { describe, expect, it } from "vitest";
import { mobileNavLinks } from "./mobile-nav";

describe("mobile navigation", () => {
  it("contains only page destinations", () => {
    expect(mobileNavLinks.map(([label]) => label)).toEqual([
      "Home",
      "Artists",
      "Songs",
      "Wins",
      "Shows",
      "About",
    ]);
  });
});
