import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SiteFooter } from "./site-shell";

describe("SiteFooter", () => {
  it("includes Wikipedia attribution, licensing, and safe external links", () => {
    const html = renderToStaticMarkup(<SiteFooter />);
    expect(html).toContain("Music-show results are derived from");
    expect(html).toContain("KpopWins is independent and is not affiliated with the Wikimedia Foundation.");
    expect(html).toContain('href="https://en.wikipedia.org/"');
    expect(html).toContain('href="https://creativecommons.org/licenses/by-sa/4.0/"');
    expect(html.match(/target="_blank"/g)).toHaveLength(2);
    expect(html.match(/rel="noopener noreferrer"/g)).toHaveLength(2);
    expect(html).toContain("Not affiliated with artists, labels, or broadcasters.");
  });
});
