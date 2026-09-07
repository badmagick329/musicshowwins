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
    expect(html).toContain('href="/artists"');
    expect(html).toContain("All artists");
  });
});
