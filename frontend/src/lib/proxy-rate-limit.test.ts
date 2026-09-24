import { afterEach, describe, expect, it } from "vitest";

import {
  checkProxyRateLimit,
  MAX_CLIENTS,
  resetProxyRateLimit,
  WINDOW_MS,
} from "./proxy-rate-limit";

afterEach(() => resetProxyRateLimit());

describe("proxy GET rate limit", () => {
  it("allows 120 requests, then returns the exact seconds until the window resets", () => {
    const now = 10 * WINDOW_MS + 12_345;

    for (let request = 0; request < 120; request += 1) {
      expect(checkProxyRateLimit("203.0.113.1", now)).toEqual({ allowed: true, retryAfter: 0 });
    }

    expect(checkProxyRateLimit("203.0.113.1", now)).toEqual({ allowed: false, retryAfter: 48 });
  });

  it("allows requests in the next aligned window", () => {
    expect(checkProxyRateLimit("203.0.113.1", WINDOW_MS - 1).allowed).toBe(true);
    expect(checkProxyRateLimit("203.0.113.1", WINDOW_MS).allowed).toBe(true);
  });

  it("evicts the oldest inserted client when the map reaches its cap", () => {
    const now = 2 * WINDOW_MS;
    for (let request = 0; request < 120; request += 1) {
      checkProxyRateLimit("oldest", now);
    }
    for (let client = 1; client < MAX_CLIENTS; client += 1) {
      checkProxyRateLimit(`client-${client}`, now);
    }

    expect(checkProxyRateLimit("new-client", now).allowed).toBe(true);
    expect(checkProxyRateLimit("oldest", now)).toEqual({ allowed: true, retryAfter: 0 });
  });
});
