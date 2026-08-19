import { afterEach, describe, expect, it, vi } from "vitest";
import { getHomeData, parseApiPage } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("parseApiPage", () => {
  it("keeps pagination metadata and typed results", () => {
    const page = parseApiPage<{ id: number }>({
      count: 1,
      next: null,
      previous: null,
      results: [{ id: 7 }],
    });
    expect(page.count).toBe(1);
    expect(page.results[0]?.id).toBe(7);
  });

  it("rejects an unpaginated or malformed API response", () => {
    expect(() => parseApiPage({ results: [] })).toThrow("invalid page");
    expect(() => parseApiPage(null)).toThrow("invalid page");
  });
});

describe("getHomeData", () => {
  it("loads the music shows used by the homepage", async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const results = String(input).includes("/shows")
        ? [{ id: 1, slug: "music-bank", name: "Music Bank", active: true }]
        : [];

      return new Response(
        JSON.stringify({ count: results.length, next: null, previous: null, results }),
        { status: 200 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const data = await getHomeData();

    expect(data.shows).toEqual([
      { id: 1, slug: "music-bank", name: "Music Bank", active: true },
    ]);
    expect(data.errors).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
