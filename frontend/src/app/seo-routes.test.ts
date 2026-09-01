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
    const fetchMock = vi.fn(async () => Response.json({
      artists: [{ id: 3, latest_win_date: "2026-08-31" }],
      songs: [{ id: 7, latest_win_date: "2026-08-30" }],
    }));
    vi.stubGlobal("fetch", fetchMock);

    const urls = (await sitemap()).map(({ url }) => url);
    expect(urls).toEqual(expect.arrayContaining([
      "https://kpopwins.info/",
      "https://kpopwins.info/artists",
      "https://kpopwins.info/artists/3",
      "https://kpopwins.info/songs/7",
    ]));
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("fails generation instead of publishing a partial sitemap", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
    await expect(sitemap()).rejects.toThrow("Sitemap source failed (503).");
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
