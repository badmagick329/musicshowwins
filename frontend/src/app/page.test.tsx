import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getHomeData: vi.fn(async () => ({ artists: [], songs: [], wins: [], shows: [], artistResults: [], artistResultCount: 0, errors: [] })),
}));
vi.mock("@/components/artist-search", () => ({ ArtistSearch: () => null }));

import Home from "./page";

describe("homepage banner", () => {
  it("uses the simplified copy without the redundant archive panel", async () => {
    const html = renderToStaticMarkup(await Home({ searchParams: Promise.resolve({}) }));
    expect(html).toContain("K-pop music show wins &amp; artist rankings");
    expect(html).toContain("Explore K-pop music show win counts for BTS, TWICE, EXO and more, with artist rankings and results from Inkigayo, Music Bank and other shows.");
    expect(html).not.toContain("clearly kept");
    expect(html).toContain('href="/shows"');
    expect(html).toContain("All shows");
    expect(html).toContain('href="/rankings"');
    expect(html).toContain("Top wins this year");
    expect(html).toContain('bg-action-pink text-white');
    expect(html).toContain('href="/rankings?kind=artists"');
    expect(html.indexOf("Most wins in")).toBeLessThan(html.indexOf("Recent wins"));
  });

  it("keeps full-ranking links aligned with the shared all-time preview", async () => {
    const html = renderToStaticMarkup(await Home({ searchParams: Promise.resolve({ rankings: "all-time" }) }));
    expect(html).toContain("Most wins of all time");
    expect(html).toContain('bg-action-pink text-white');
    expect(html).toContain('href="/rankings?kind=artists&amp;period=all-time"');
    expect(html).toContain('href="/rankings?period=all-time"');
    expect(html.indexOf("Most wins of all time")).toBeLessThan(html.indexOf("Recent wins"));
  });

  it("keeps an artist search when changing preview period", async () => {
    const html = renderToStaticMarkup(await Home({ searchParams: Promise.resolve({ search: "BTS & friends" }) }));
    expect(html).toContain('href="/?search=BTS%20%26%20friends&amp;rankings=all-time"');
  });
});
