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
    expect(html).toContain("Explore K-pop music show wins.");
    expect(html).toContain("Search artists, songs, and weekly music-show winners from 2014 onward.");
    expect(html).not.toContain("2014–today");
    expect(html).not.toContain("Six weekly music shows in one searchable archive.");
  });
});
