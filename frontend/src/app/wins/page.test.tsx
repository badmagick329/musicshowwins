import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError } from "@/lib/api-shared";
import WinsPage from "./page";

const { redirectMock, requestPageMock } = vi.hoisted(() => ({
  redirectMock: vi.fn(() => { throw new Error("NEXT_REDIRECT"); }),
  requestPageMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({ redirect: redirectMock }));
vi.mock("@/lib/api-server", () => ({
  serverTransport: {
    requestPage: requestPageMock,
    requestDetail: vi.fn(),
  },
}));

describe("wins page", () => {
  beforeEach(() => {
    redirectMock.mockClear();
    requestPageMock.mockReset();
  });

  it("redirects an out-of-range deep link to the first page", async () => {
    requestPageMock.mockRejectedValueOnce(new ApiRequestError(404));

    await expect(WinsPage({ searchParams: Promise.resolve({ page: "99" }) })).rejects.toThrow("NEXT_REDIRECT");
    expect(redirectMock).toHaveBeenCalledWith("/wins");
  });

  it("does not request wins for malformed date parameters", async () => {
    requestPageMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });

    await WinsPage({ searchParams: Promise.resolve({ date_from: "abc" }) });

    expect(requestPageMock).toHaveBeenCalledTimes(1);
    expect(requestPageMock).toHaveBeenCalledWith("/shows", undefined, expect.any(AbortSignal));
  });
});
