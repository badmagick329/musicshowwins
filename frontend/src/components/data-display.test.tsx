import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ShowBadge } from "./data-display";

describe("ShowBadge", () => {
  it("keeps the accessible show name and stable colour class without a decorative dot", () => {
    const html = renderToStaticMarkup(<ShowBadge slug="music-bank" name="Music Bank" />);
    expect(html).toContain("Music Bank");
    expect(html).toContain("show-music-bank");
    expect(html).not.toContain("show-dot");
    expect(html).not.toContain("aria-hidden");
  });
});
