import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("./mobile-nav", () => ({ MobileNav: () => <button type="button">Menu</button> }));

import { SiteFooter, SiteHeader } from "./site-shell";

describe("SiteHeader", () => {
  it("uses the reusable brand mark without duplicating the labelled home link", () => {
    const html = renderToStaticMarkup(<SiteHeader />);
    expect(html).toContain('aria-label="KpopWins home"');
    expect(html).toContain('data-brand-mark="true"');
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain(">KpopWins</span>");
    expect(html).not.toContain(">K</span>");
  });
});

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
