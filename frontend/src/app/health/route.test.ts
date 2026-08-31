import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("frontend health", () => {
  it("reports only that Next.js is running", async () => {
    const response = GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true });
  });
});
