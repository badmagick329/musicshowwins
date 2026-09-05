import { afterEach, describe, expect, it, vi } from "vitest";

const { revalidateTag } = vi.hoisted(() => ({ revalidateTag: vi.fn() }));
vi.mock("next/cache", () => ({ revalidateTag }));

import { POST } from "./route";

afterEach(() => {
  vi.unstubAllEnvs();
  revalidateTag.mockReset();
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

  it("immediately expires the shared archive tag", async () => {
    vi.stubEnv("CACHE_REVALIDATION_SECRET", "correct-secret");
    const response = await POST(new Request("http://localhost/api/revalidate", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret" },
    }));
    expect(response.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("public-archive", { expire: 0 });
  });
});
