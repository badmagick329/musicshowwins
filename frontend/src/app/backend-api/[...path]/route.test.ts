import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { GET, POST } from "./route";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

function context(...path: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe("backend API proxy", () => {
  it("proxies GET requests with query strings and preserves status and content type", async () => {
    vi.stubEnv("DJANGO_API_BASE_URL", "http://backend:8000/api/v1");
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
      new NextRequest("https://kpopwins.info/backend-api/wins?page=2&show=music-bank"),
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
        headers: { "Content-Type": "application/json", Cookie: "private=value" },
        body: '{"record":"fixed"}',
      }),
      context("corrections"),
    );

    expect(response.status).toBe(202);
    expect(await response.json()).toEqual({ detail: "accepted" });
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
