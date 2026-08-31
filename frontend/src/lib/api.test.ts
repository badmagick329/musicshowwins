import { afterEach, describe, expect, it, vi } from "vitest";
import { parseApiPage, parsePositivePage } from "./api-shared";
import { buildServerApiUrl, collectPages, getArtist, getArtists, getHomeData, serverRequestPage } from "./api-server";
import { submitCorrection } from "./api-browser";

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => new Headers({
    "x-forwarded-for": "203.0.113.25",
    "x-real-ip": "203.0.113.25",
  })),
}));

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("API URLs and pagination", () => {
  it("encodes query parameters", () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "https://example.test/api/v1/");
    expect(buildServerApiUrl("/artists", { search: "Girls' Generation & 소녀시대", page: 2 })).toBe("https://example.test/api/v1/artists?search=Girls%27+Generation+%26+%EC%86%8C%EB%85%80%EC%8B%9C%EB%8C%80&page=2");
  });

  it("keeps valid pagination metadata and rejects malformed pages", () => {
    expect(parseApiPage<{ id: number }>({ count: 1, next: "?page=2", previous: null, results: [{ id: 7 }] })).toEqual({ count: 1, next: "?page=2", previous: null, results: [{ id: 7 }] });
    expect(() => parseApiPage({ results: [] })).toThrow("invalid page");
    expect(() => parseApiPage({ count: 0, next: 4, previous: null, results: [] })).toThrow("invalid page");
  });

  it("collects each page in the API sequence", async () => {
    const load = vi.fn(async (page: number) => page === 1
      ? { count: 2, next: "http://127.0.0.1:8000/api/v1/wins?page=2", previous: null, results: [1] }
      : { count: 2, next: null, previous: "http://127.0.0.1:8000/api/v1/wins", results: [2] });
    await expect(collectPages("/wins", {}, load)).resolves.toEqual([1, 2]);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("stops repeated and malformed next-page links", async () => {
    const repeated = async () => ({ count: 2, next: "http://127.0.0.1:8000/api/v1/wins?page=1", previous: null, results: [1] });
    await expect(collectPages("/wins", {}, repeated)).rejects.toThrow("malformed pagination");
    const wrongPath = async () => ({ count: 2, next: "http://127.0.0.1:8000/api/v1/artists?page=2", previous: null, results: [1] });
    await expect(collectPages("/wins", {}, wrongPath)).rejects.toThrow("malformed pagination");
  });
});

describe("request failures and input", () => {
  it("sends the forwarded HTTPS header for server page requests", async () => {
    const fetchMock = vi.fn<(input: string | URL | Request, init?: RequestInit) => Promise<Response>>(async () =>
      new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] })));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await serverRequestPage("/artists", {}, controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/artists"),
      expect.objectContaining({
        cache: "no-store",
        headers: {
          "X-Forwarded-For": "203.0.113.25",
          "X-Forwarded-Proto": "https",
          "X-Real-IP": "203.0.113.25",
        },
        signal: controller.signal,
      }),
    );
  });

  it("sends the forwarded HTTPS header for server detail requests", async () => {
    const fetchMock = vi.fn<(input: string | URL | Request, init?: RequestInit) => Promise<Response>>(async () =>
      new Response(JSON.stringify({ id: 8, name: "Artist" })));
    vi.stubGlobal("fetch", fetchMock);

    await getArtist(8);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/artists/8"),
      expect.objectContaining({
        cache: "no-store",
        headers: {
          "X-Forwarded-For": "203.0.113.25",
          "X-Forwarded-Proto": "https",
          "X-Real-IP": "203.0.113.25",
        },
      }),
    );
  });

  it("posts correction reports through the same-origin API boundary", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "Report accepted." }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const report = { page_or_record: "A record", correction: "A correction", supporting_source: "", contact: "", website: "" };
    await submitCorrection(report);
    expect(fetchMock).toHaveBeenCalledWith("/backend-api/corrections", expect.objectContaining({ method: "POST", body: JSON.stringify(report) }));
  });

  it("distinguishes not found from general failures", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
    await expect(getArtist(8)).rejects.toMatchObject({ status: 404, name: "ApiRequestError" });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
    await expect(getArtist(8)).rejects.toMatchObject({ status: 503, name: "ApiRequestError" });
  });

  it("defaults invalid page values to one", () => {
    expect(parsePositivePage(undefined)).toBe(1);
    expect(parsePositivePage("0")).toBe(1);
    expect(parsePositivePage("-2")).toBe(1);
    expect(parsePositivePage("nope")).toBe(1);
    expect(parsePositivePage(["2"])).toBe(1);
    expect(parsePositivePage("3")).toBe(3);
  });
});

describe("artist ordering", () => {
  it.each([
    [undefined, "-total_wins,name"],
    ["wins", "-total_wins,name"],
    ["name", "name"],
    ["name-desc", "-name"],
  ] as const)("maps %s to the supported API ordering", async (sort, ordering) => {
    const fetchMock = vi.fn<(input: string | URL | Request) => Promise<Response>>(async () => new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await getArtists("bts", 2, sort);
    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.searchParams.get("search")).toBe("bts");
    expect(url.searchParams.get("page")).toBe("2");
    expect(url.searchParams.get("ordering")).toBe(ordering);
  });
});

describe("getHomeData", () => {
  it("loads the music shows used by the homepage", async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const results = String(input).includes("/shows") ? [{ id: 1, slug: "music-bank", name: "Music Bank", active: true }] : [];
      return new Response(JSON.stringify({ count: results.length, next: null, previous: null, results }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const data = await getHomeData();
    expect(data.shows).toEqual([{ id: 1, slug: "music-bank", name: "Music Bank", active: true }]);
    expect(data.errors).toEqual([]);
    expect(data.artistResultCount).toBe(0);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("preserves the full artist result count while limiting the homepage rows", async () => {
    const artists = Array.from({ length: 10 }, (_, index) => ({ id: index, name: `Artist ${index}`, total_wins: 10 - index, winning_songs: 1, latest_win_date: "2025-01-01" }));
    vi.stubGlobal("fetch", vi.fn(async (input: string | URL | Request) => {
      const isArtists = String(input).includes("/artists?");
      return new Response(JSON.stringify({ count: isArtists ? 12 : 0, next: isArtists ? "?page=2" : null, previous: null, results: isArtists ? artists : [] }), { status: 200 });
    }));
    const data = await getHomeData("artist");
    expect(data.artistResultCount).toBe(12);
    expect(data.artistResults).toHaveLength(8);
  });
});
