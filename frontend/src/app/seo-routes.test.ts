import { afterEach, describe, expect, it, vi } from "vitest";
import robots from "./robots";
import sitemap from "./sitemap";
import { GET as llms } from "./llms.txt/route";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SEO and agent discovery routes", () => {
  it("allows public crawling while excluding internal endpoints", () => {
    expect(robots()).toEqual({
      rules: {
        userAgent: "*",
        allow: "/",
        disallow: ["/backend-api/", "/health", "/ingest/"],
      },
      sitemap: "https://kpopwins.info/sitemap.xml",
      host: "https://kpopwins.info",
    });
  });

  it("lists canonical static and entity pages", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string | URL | Request) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/artists")) {
        return Response.json({ count: 1, next: null, previous: null, results: [{ id: 3, name: "aespa", total_wins: 12, winning_songs: 4, latest_win_date: "2026-08-31" }] });
      }
      return Response.json({ count: 1, next: null, previous: null, results: [{ id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 3, winning_shows: 2, latest_win_date: "2026-08-30" }] });
    }));

    const urls = (await sitemap()).map(({ url }) => url);
    expect(urls).toEqual(expect.arrayContaining([
      "https://kpopwins.info/",
      "https://kpopwins.info/artists",
      "https://kpopwins.info/artists/3",
      "https://kpopwins.info/songs/7",
    ]));
  });

  it("keeps static discovery available when the data API fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
    const entries = await sitemap();
    expect(entries).toHaveLength(6);
    expect(entries.some(({ url }) => url === "https://kpopwins.info/wins")).toBe(true);
  });

  it("publishes concise agent guidance as markdown", async () => {
    const response = llms();
    const body = await response.text();
    expect(response.headers.get("content-type")).toContain("text/markdown");
    expect(body).toContain("# KpopWins");
    expect(body).toContain("https://kpopwins.info/sitemap.xml");
    expect(body).toContain("Query-string URLs are filtered or sorted views");
  });
});
