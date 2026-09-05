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
  it("rejects missing and incorrect credentials", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate", {
      method: "POST",
      headers: { Authorization: "Bearer incorrect-secret" },
    }));
    expect(response.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("expires the shared archive tag and warms the canonical pages", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("public-archive", { expire: 0 });
    expect(warmCanonicalArchivePages).toHaveBeenCalledOnce();
    await expect(response.json()).resolves.toEqual({ revalidated: true, warmed: true });
  });

  it("reports a warming failure after invalidating the cache", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    warmCanonicalArchivePages.mockRejectedValueOnce(new Error("API unavailable"));
    const response = await POST(new Request("http://localhost/api/revalidate", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(502);
    expect(revalidateTag).toHaveBeenCalledWith("public-archive", { expire: 0 });
    await expect(response.json()).resolves.toEqual({
      detail: "Cache was invalidated, but canonical pages could not be warmed.",
      revalidated: true,
      warmed: false,
    });
  });
});
