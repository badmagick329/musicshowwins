import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { GET, POST } from "./route";
import { resetProxyRateLimit } from "@/lib/proxy-rate-limit";

afterEach(() => {
  resetProxyRateLimit();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function context(...path: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe("backend API proxy", () => {
  it("uses the server API default for browser requests when no URL is configured", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "");
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      void input;
      return new Response('{"count":0,"next":null,"previous":null,"results":[]}', { headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(new NextRequest("http://localhost:3000/backend-api/leaderboards/artists?date_from=2026-01-01"), context("leaderboards", "artists"));
    expect(response.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("http://127.0.0.1:8000/api/v1/leaderboards/artists?date_from=2026-01-01");
  });

  it("proxies GET requests with query strings and preserves status and content type", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    vi.stubEnv("INTERNAL_API_SECRET", "internal-secret");
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      void input;
      void init;
      return new Response(JSON.stringify({
        count: 1,
        next: "https://backend:8000/api/v1/wins?page=3",
      }), {
        status: 206,
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(
      new NextRequest("https://kpopwins.info/backend-api/wins?page=2&show=music-bank", {
        headers: {
          "x-forwarded-for": "203.0.113.25",
          "x-real-ip": "203.0.113.25",
        },
      }),
      context("wins"),
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0]!;
    expect(options).toBeDefined();
    if (!options) throw new Error("Expected proxy request options");
    const headers = new Headers(options.headers);
    expect(String(url)).toBe("http://backend:8000/api/v1/wins?page=2&show=music-bank");
    expect(options.method).toBe("GET");
    expect(options.credentials).toBe("omit");
    expect(headers.get("X-Forwarded-Proto")).toBe("https");
    expect(headers.get("X-KpopWins-Internal-Key")).toBe("internal-secret");
    expect(headers.has("X-Forwarded-For")).toBe(false);
    expect(headers.has("X-Real-IP")).toBe(false);
    expect(options.next).toEqual({ revalidate: 86400, tags: ["public-archive"] });
    expect(headers.has("cookie")).toBe(false);
    expect(headers.has("host")).toBe(false);
    expect(response.status).toBe(206);
    expect(response.headers.get("content-type")).toBe("application/json; charset=utf-8");
    const body = await response.text();
    expect(JSON.parse(body)).toEqual({
      count: 1,
      next: "/backend-api/wins?page=3",
    });
    expect(body).not.toContain("backend:8000");
  });

  it("proxies POST bodies and their content type", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    const fetchMock = vi.fn(async (_url: URL, options: RequestInit) => {
      expect(options.headers instanceof Headers && options.headers.get("Content-Type")).toBe("application/json");
      expect(options.headers instanceof Headers && options.headers.has("X-KpopWins-Internal-Key")).toBe(false);
      expect(options.headers instanceof Headers && options.headers.get("X-Forwarded-For")).toBe("203.0.113.25");
      expect(options.headers instanceof Headers && options.headers.get("X-Real-IP")).toBe("203.0.113.25");
      expect(options.cache).toBe("no-store");
      expect(new TextDecoder().decode(options.body as ArrayBuffer)).toBe('{"record":"fixed"}');
      return new Response('{"detail":"accepted"}', {
        status: 202,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new NextRequest("https://kpopwins.info/backend-api/corrections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: "private=value",
          "X-Forwarded-For": "203.0.113.25",
          "X-Real-IP": "203.0.113.25",
        },
        body: '{"record":"fixed"}',
      }),
      context("corrections"),
    );

    expect(response.status).toBe(202);
    expect(await response.json()).toEqual({ detail: "accepted" });
  });

  it.each([[".."], ["."], ["wins", ""]])("rejects unsafe path segments %j without fetching", async (...path) => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(new NextRequest("https://kpopwins.info/backend-api/wins"), context(...path));

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Not found." });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("limits GETs by the last forwarded IP and allows another IP", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    const fetchMock = vi.fn(async () => new Response("{}", { headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    for (let index = 0; index < 120; index += 1) {
      await GET(new NextRequest("https://kpopwins.info/backend-api/wins", {
        headers: { "x-forwarded-for": `spoofed-${index}, 203.0.113.25` },
      }), context("wins"));
    }
    const limited = await GET(new NextRequest("https://kpopwins.info/backend-api/wins", {
      headers: { "x-forwarded-for": "another-spoof, 203.0.113.25" },
    }), context("wins"));
    const otherClient = await GET(new NextRequest("https://kpopwins.info/backend-api/wins", {
      headers: { "x-forwarded-for": "203.0.113.26" },
    }), context("wins"));

    expect(limited.status).toBe(429);
    expect(limited.headers.get("Retry-After")).toBeTruthy();
    expect(await limited.json()).toEqual({ detail: "Too many requests." });
    expect(otherClient.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(121);
  });

  it("resets the GET window after 60 seconds and does not count POSTs", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-24T12:00:00Z"));
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    const fetchMock = vi.fn(async () => new Response("{}", { headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const clientHeaders = { "x-forwarded-for": "203.0.113.25" };

    await POST(new NextRequest("https://kpopwins.info/backend-api/corrections", {
      method: "POST", headers: { ...clientHeaders, "Content-Type": "application/json" }, body: "{}",
    }), context("corrections"));
    for (let index = 0; index < 120; index += 1) {
      await GET(new NextRequest("https://kpopwins.info/backend-api/wins", { headers: clientHeaders }), context("wins"));
    }
    const limited = await GET(new NextRequest("https://kpopwins.info/backend-api/wins", { headers: clientHeaders }), context("wins"));
    vi.advanceTimersByTime(60_000);
    const afterReset = await GET(new NextRequest("https://kpopwins.info/backend-api/wins", { headers: clientHeaders }), context("wins"));

    expect(limited.status).toBe(429);
    expect(afterReset.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(122);
  });

  it("returns a generic failure without exposing the internal URL", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("connect ECONNREFUSED http://backend:8000"); }));

    const response = await GET(
      new NextRequest("https://kpopwins.info/backend-api/wins"),
      context("wins"),
    );
    const body = await response.text();

    expect(response.status).toBe(502);
    expect(body).toContain("Backend service unavailable");
    expect(body).not.toContain("backend:8000");
    expect(body).not.toContain("DJANGO_API_BASE_URL");
  });
});
