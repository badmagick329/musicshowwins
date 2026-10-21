import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { cache, cacheOptions } = vi.hoisted(() => ({
  cache: new Map<string, unknown>(),
  cacheOptions: [] as unknown[],
}));
vi.mock("next/cache", () => ({
  unstable_cache: (load: (...args: string[]) => Promise<unknown>, keys: string[], options: unknown) => {
    cacheOptions.push(options);
    return async (...args: string[]) => {
      const key = JSON.stringify([keys, args]);
      if (cache.has(key)) return structuredClone(cache.get(key));
      const result = await load(...args);
      cache.set(key, structuredClone(result));
      return result;
    };
  },
}));
vi.mock("@/components/debounced-artist-search", () => ({ DebouncedArtistSearch: () => null }));

import ArtistsPage from "@/app/artists/(index)/page";
import { generateMetadata as artistMetadata } from "@/app/artists/[slug]/page";
import { generateMetadata as songMetadata } from "@/app/songs/[id]/page";
import { GET } from "@/app/backend-api/[...path]/route";
import { proxy } from "@/proxy";
import { getArtists, warmCanonicalArchivePages } from "@/lib/api-server";
import { canonicalArchiveUrl, readArchive, warmArchive } from "./archive-read";
import { resetProxyRateLimit } from "./proxy-rate-limit";

beforeEach(() => {
  cache.clear();
  vi.stubEnv("INTERNAL_API_SECRET", "trusted-secret");
  vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  resetProxyRateLimit();
});

function publicBackend(allowance: number) {
  let expensiveReads = 0;
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    expect(headers.get("X-KpopWins-Internal-Key")).toBe("trusted-secret");
    expect(headers.get("X-KpopWins-Public-Read")).toBe("1");
    if (expensiveReads >= allowance) return Response.json({ detail: "Too many requests." }, { status: 429, headers: { "Retry-After": "42" } });
    expensiveReads += 1;
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, expensiveReads: () => expensiveReads };
}

describe("public archive data boundary", () => {
  it("keeps rotating SSR searches, detail metadata and both proxies on the same backend budget", async () => {
    const backend = publicBackend(2);
    await ArtistsPage({ searchParams: Promise.resolve({ search: "first-miss" }) });
    await ArtistsPage({ searchParams: Promise.resolve({ search: "second-miss" }) });
    await expect(ArtistsPage({ searchParams: Promise.resolve({ search: "third-miss", sort: "name", page: "2" }) })).rejects.toMatchObject({ status: 429 });
    await expect(artistMetadata({ params: Promise.resolve({ slug: "uncached-artist" }) })).rejects.toMatchObject({ status: 429 });
    await expect(songMetadata({ params: Promise.resolve({ id: "999" }) })).rejects.toMatchObject({ status: 429 });
    const browser = await GET(new NextRequest("https://kpopwins.info/backend-api/wins?search=another-miss", {
      headers: { "X-KpopWins-Public-Read": "0", "X-KpopWins-Internal-Key": "attacker-key" },
    }), { params: Promise.resolve({ path: ["wins"] }) });
    const legacy = await proxy(new NextRequest("https://kpopwins.info/artists/998"));
    expect(browser.status).toBe(429);
    expect(legacy.status).toBe(429);
    expect(browser.headers.get("Retry-After")).toBe("42");
    expect(legacy.headers.get("Retry-After")).toBe("42");
    expect(backend.expensiveReads()).toBe(2);
    const calls = backend.fetchMock.mock.calls.length;
    // Exhaustion cannot poison an existing successful cached page.
    await ArtistsPage({ searchParams: Promise.resolve({ search: " first-miss " }) });
    expect(backend.fetchMock).toHaveBeenCalledTimes(calls);
  });

  it("warms privately and reuses that same cache from public SSR and browser reads", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("X-KpopWins-Internal-Key")).toBe("trusted-secret");
      expect(headers.has("X-KpopWins-Public-Read")).toBe(false);
      return Response.json({ count: 0, next: null, previous: null, results: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    await warmCanonicalArchivePages();
    const privateFills = fetchMock.mock.calls.length;
    expect(privateFills).toBeGreaterThan(0);
    await ArtistsPage({ searchParams: Promise.resolve({}) });
    const browser = await GET(new NextRequest("https://kpopwins.info/backend-api/artists?page=01&ordering=-total_wins,name&ignored=cache-buster"), {
      params: Promise.resolve({ path: ["artists"] }),
    });
    expect(browser.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(privateFills);
    expect(cacheOptions).toContainEqual({ revalidate: 86400, tags: ["public-archive"] });

    // The warmer's private context ends before the next public cache miss.
    const backend = publicBackend(1);
    await getArtists("new-public-search");
    expect(backend.expensiveReads()).toBe(1);
  });

  it("does not cache rejected backend work, allowing recovery after the budget resets", async () => {
    const backend = publicBackend(0);
    await expect(getArtists("retry")).rejects.toMatchObject({ status: 429 });
    await expect(getArtists("retry")).rejects.toMatchObject({ status: 429 });
    expect(backend.fetchMock).toHaveBeenCalledTimes(2);
    const recovered = publicBackend(1);
    await getArtists("retry");
    expect(recovered.expensiveReads()).toBe(1);
  });

  it("charges numeric redirect lookups publicly even when the app has a privately warmed detail", async () => {
    const fetchMock = vi.fn<(url: string, options?: RequestInit) => Promise<Response>>(async () => Response.json({ id: 8, slug: "artist" }));
    vi.stubGlobal("fetch", fetchMock);
    const url = "http://backend:8000/api/v1/artists/8";
    await warmArchive(() => readArchive(url));
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).has("X-KpopWins-Public-Read")).toBe(false);

    // The explicit public reader must not inherit private warming authority.
    const first = await warmArchive(() => proxy(new NextRequest("https://kpopwins.info/artists/0008")));
    const second = await proxy(new NextRequest("https://kpopwins.info/artists/8"));
    expect(first.status).toBe(308);
    expect(second.status).toBe(308);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const [target, options] of fetchMock.mock.calls.slice(1)) {
      expect(target).toBe(url);
      expect(new Headers(options?.headers).get("X-KpopWins-Public-Read")).toBe("1");
    }
    await readArchive(url);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("handles caller aborts without cancelling a shared backend fill", async () => {
    const backend = publicBackend(1);
    const cancelled = new AbortController();
    cancelled.abort();
    await expect(readArchive("http://backend:8000/api/v1/shows", cancelled.signal)).rejects.toMatchObject({ name: "AbortError" });
    expect(backend.fetchMock).not.toHaveBeenCalled();
    await readArchive("http://backend:8000/api/v1/shows");
    expect(backend.fetchMock.mock.calls[0][1]?.signal).toBeUndefined();
  });
});

describe("archive cache inputs", () => {
  it("canonicalizes ignored query keys, duplicates, whitespace and numeric spellings", () => {
    expect(canonicalArchiveUrl("http://backend/api/v1/wins/?noise=a&page=0002&search=%20BTS%20&search=ignored&ordering=%20-date%20"))
      .toBe("http://backend/api/v1/wins?search=BTS&ordering=-date&page=2");
    expect(canonicalArchiveUrl("http://backend/api/v1/artists/0008?noise=b")).toBe("http://backend/api/v1/artists/8");
  });

  it.each([
    "/wins?page=1000001", "/wins?ordering=date,date", "/wins?search=" + "x".repeat(201),
    "/wins?date_from=2026-02-30", "/leaderboards/songs?limit=1001", "/songs/9007199254740992", "/admin",
  ])("rejects unsupported or unbounded input %s before backend work", async (path) => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(readArchive(`http://backend/api/v1${path}`)).rejects.toBeInstanceOf(Error);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
