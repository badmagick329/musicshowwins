import { afterEach, describe, expect, it, vi } from "vitest";

const { revalidateTag, warmCanonicalArchivePages } = vi.hoisted(() => ({
  revalidateTag: vi.fn(),
  warmCanonicalArchivePages: vi.fn(),
}));
vi.mock("next/cache", () => ({ revalidateTag }));
vi.mock("@/lib/api-server", () => ({
  publicArchiveCacheTag: "public-archive",
  warmCanonicalArchivePages,
}));

import { POST } from "./route";

afterEach(() => {
  vi.unstubAllEnvs();
  revalidateTag.mockReset();
  warmCanonicalArchivePages.mockReset();
});

describe("archive cache revalidation", () => {
  it.each([undefined, "Bearer incorrect-secret"])("rejects missing and incorrect credentials before validating action (%s)", async (authorization) => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate", {
      method: "POST",
      headers: authorization ? { Authorization: authorization } : {},
    }));
    expect(response.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
    expect(warmCanonicalArchivePages).not.toHaveBeenCalled();
  });

  it("expires the shared archive tag without warming in the same request", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate?action=invalidate", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("public-archive", { expire: 0 });
    expect(warmCanonicalArchivePages).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({ revalidated: true });
  });

  it("warms canonical pages without invalidating their fresh entries", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate?action=warm", {
      method: "POST", headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(200);
    expect(revalidateTag).not.toHaveBeenCalled();
    expect(warmCanonicalArchivePages).toHaveBeenCalledOnce();
    await expect(response.json()).resolves.toEqual({ warmed: true });
  });

  it.each(["", "?action=unknown", "?action=warm&action=invalidate"])("rejects missing or unsupported action %s without work", async (query) => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request(`http://localhost/api/revalidate${query}`, {
      method: "POST", headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(400);
    expect(revalidateTag).not.toHaveBeenCalled();
    expect(warmCanonicalArchivePages).not.toHaveBeenCalled();
  });

  it("reports a warming failure without invalidating the cache", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    warmCanonicalArchivePages.mockRejectedValueOnce(new Error("API unavailable"));
    const response = await POST(new Request("http://localhost/api/revalidate?action=warm", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(502);
    expect(revalidateTag).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({
      detail: "Canonical pages could not be warmed.",
      warmed: false,
    });
  });
});
