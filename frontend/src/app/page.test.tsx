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
    expect(html).toContain("K-pop music show wins since 2014.");
    expect(html).toContain("Search by artist or song and browse results from six weekly shows.");
    expect(html).not.toContain("clearly kept");
    expect(html).not.toContain("Explore K-pop");
    expect(html).toContain('href="/shows"');
    expect(html).toContain("All shows");
  });
});
