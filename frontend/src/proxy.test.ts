import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
import { config, proxy } from "./proxy";

afterEach(() => vi.unstubAllGlobals());

describe("legacy artist URL proxy", () => {
  it("permanently redirects a numeric artist URL to its slug, keeping the query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 137, slug: "stray-kids" })));
    vi.stubGlobal("fetch", fetchMock);
    const response = await proxy(new NextRequest("https://kpopwins.info/artists/137?year=2024"));
    expect(response.status).toBe(308);
    expect(response.headers.get("location")).toBe("https://kpopwins.info/artists/stray-kids?year=2024");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/artists\/137$/);
  });

  it("lets unknown IDs through to the page's not-found handling", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
    const response = await proxy(new NextRequest("https://kpopwins.info/artists/99999"));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it("only matches numeric artist paths", () => {
    expect(config.matcher).toBe("/artists/:id([0-9]+)");
  });
});
