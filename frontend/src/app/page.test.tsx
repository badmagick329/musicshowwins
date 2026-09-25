import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getHomeData: vi.fn(async () => ({
    artists: [],
    songs: [],
    week: { start: "2026-09-14", end: "2026-09-20", current: false, wins: [{ id: 9, date: "2026-09-20", show: { id: 6, slug: "inkigayo", name: "Inkigayo", active: true }, song: { id: 4, title: "Bad", artist: { id: 2, name: "Ateez" }, total_wins: 7, winning_shows: 4, latest_win_date: "2026-09-20" }, references: [], milestones: { song_win: 7, song_show_win: 3, artist_win: 40 } }] },
    shows: [{ id: 5, slug: "music-core", name: "Show! Music Core", active: true }, { id: 6, slug: "inkigayo", name: "Inkigayo", active: true }],
    artistResults: [],
    artistResultCount: 0,
    errors: [],
  })),
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
    expect(html).not.toContain("Recent wins");
    expect(html.indexOf("Latest results · 14–20 Sept")).toBeLessThan(html.indexOf("Most wins in"));
    expect(html).toContain("No results yet this week.");
    expect(html).toContain("7th recorded win for Bad");
    expect(html).toContain("Triple crown · Inkigayo");
    expect(html).toContain("No result recorded");
  });

  it("keeps full-ranking links aligned with the shared all-time preview", async () => {
    const html = renderToStaticMarkup(await Home({ searchParams: Promise.resolve({ rankings: "all-time" }) }));
    expect(html).toContain("Most wins of all time");
    expect(html).toContain('bg-action-pink text-white');
    expect(html).toContain('href="/rankings?kind=artists&amp;period=all-time"');
    expect(html).toContain('href="/rankings?period=all-time"');
    expect(html.indexOf("Latest results")).toBeLessThan(html.indexOf("Most wins of all time"));
  });

  it("keeps an artist search when changing preview period", async () => {
    const html = renderToStaticMarkup(await Home({ searchParams: Promise.resolve({ search: "BTS & friends" }) }));
    expect(html).toContain('href="/?search=BTS%20%26%20friends&amp;rankings=all-time"');
  });
});
