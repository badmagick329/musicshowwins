import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./mobile-nav", () => ({ MobileNav: () => <button type="button">Menu</button> }));

import { SiteFooter, SiteHeader } from "./site-shell";

afterEach(() => vi.unstubAllEnvs());

describe("SiteHeader", () => {
  it("uses the reusable brand mark without duplicating the labelled home link", () => {
    const html = renderToStaticMarkup(<SiteHeader />);
    expect(html).toContain('aria-label="KpopWins home"');
    expect(html).toContain('data-brand-mark="true"');
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain(">KpopWins</span>");
    expect(html).not.toContain(">K</span>");
    expect(html).toContain('href="/shows"');
    expect(html).toContain('href="/about"');
    expect(html).not.toContain('href="/#shows"');
  });
});

describe("SiteFooter", () => {
  it("includes Wikipedia attribution, licensing, and safe external links", () => {
    vi.stubEnv("SUPPORT_URL", "");
    const html = renderToStaticMarkup(<SiteFooter />);
    expect(html).toContain("Music-show results are derived from");
    expect(html).toContain("KpopWins is independent and is not affiliated with the Wikimedia Foundation.");
    expect(html).toContain('href="https://en.wikipedia.org/"');
    expect(html).toContain('href="https://creativecommons.org/licenses/by-sa/4.0/"');
    expect(html.match(/target="_blank"/g)).toHaveLength(2);
    expect(html.match(/rel="noopener noreferrer"/g)).toHaveLength(2);
    expect(html).toContain("Not affiliated with artists, labels, or broadcasters.");
  });

  it("renders a safe coffee button for a valid support URL", () => {
    vi.stubEnv("SUPPORT_URL", "https://support.example/kpopwins");
    const html = renderToStaticMarkup(<SiteFooter />);
    expect(html).toContain('href="https://support.example/kpopwins"');
    expect(html).toContain("Buy me a coffee");
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("lucide-coffee");
    expect(html).toContain("bg-highlight-yellow");
  });

  it.each([undefined, "", "not a URL", "javascript:alert(1)"])("omits the coffee button for %s", (supportUrl) => {
    vi.stubEnv("SUPPORT_URL", supportUrl);
    const html = renderToStaticMarkup(<SiteFooter />);
    expect(html).not.toContain("Buy me a coffee");
  });
});
