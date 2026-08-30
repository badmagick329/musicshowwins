import { describe, expect, it } from "vitest";
import { mobileNavLinks } from "./mobile-nav";

describe("mobileNavLinks", () => {
  it("links Shows and About to their public pages", () => {
    expect(mobileNavLinks).toContainEqual(["Shows", "/shows"]);
    expect(mobileNavLinks).toContainEqual(["About", "/about"]);
    expect(mobileNavLinks).not.toContainEqual(["Shows", "/#shows"]);
    expect(mobileNavLinks).not.toContainEqual(["About", "/#about"]);
  });
});
