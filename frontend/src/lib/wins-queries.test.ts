import { dehydrate, hydrate, QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, type ApiTransport } from "./api-shared";
import { buildBrowserApiUrl, browserRequestPage } from "./api-browser";
import { archiveStaleTime, retryArchiveRequest } from "./query-client";
import { defaultWinsFilters } from "./wins-filters";
import { queryKeys, showsQueryOptions, winsQueryOptions } from "./wins-queries";

afterEach(() => vi.unstubAllGlobals());

describe("wins queries", () => {
  it("uses stable keys for equivalent normalized filters and changes for response filters", () => {
    const defaults = defaultWinsFilters();
    expect(queryKeys.wins.list(defaults)).toEqual(queryKeys.wins.list({ ...defaults, search: "  " }));
    expect(queryKeys.wins.list(defaults)).not.toEqual(queryKeys.wins.list({ ...defaults, page: 2 }));
    expect(queryKeys.wins.list(defaults)).not.toEqual(queryKeys.wins.list({ ...defaults, show: "music-bank" }));
  });

  it("forwards TanStack Query abort signals to the transport", async () => {
    const signal = new AbortController().signal;
    const transport: ApiTransport = { requestPage: vi.fn(async () => ({ count: 0, next: null, previous: null, results: [] })) };
    const queryFn = winsQueryOptions(defaultWinsFilters(), transport).queryFn;
    if (!queryFn) throw new Error("Expected wins query function");
    await queryFn({ queryKey: queryKeys.wins.list(defaultWinsFilters()), signal, meta: undefined, client: new QueryClient() });
    expect(transport.requestPage).toHaveBeenCalledWith("/wins", expect.any(Object), signal);
  });

  it("uses the same-origin browser API path and forwards its signal", async () => {
    const signal = new AbortController().signal;
    const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(async () => new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] })));
    vi.stubGlobal("fetch", fetchMock);
    await browserRequestPage("/wins", { page: 1 }, signal);
    expect(buildBrowserApiUrl("/wins", { page: 1 })).toBe("/backend-api/wins?page=1");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/backend-api/wins?page=1");
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ signal });
  });

  it("keeps hydrated data fresh without an immediate browser fetch", async () => {
    const response = { count: 1, next: null, previous: null, results: [{ id: 1 }] };
    const serverRequest = vi.fn(async () => response);
    const browserRequest = vi.fn(async () => response);
    const server: ApiTransport = { requestPage: serverRequest as ApiTransport["requestPage"] };
    const browser: ApiTransport = { requestPage: browserRequest as ApiTransport["requestPage"] };
    const serverClient = new QueryClient({ defaultOptions: { queries: { staleTime: archiveStaleTime } } });
    await serverClient.prefetchQuery(winsQueryOptions(defaultWinsFilters(), server));
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: archiveStaleTime } } });
    hydrate(client, dehydrate(serverClient));
    await client.fetchQuery(winsQueryOptions(defaultWinsFilters(), browser));
    expect(browserRequest).not.toHaveBeenCalled();
  });

  it("retries network and 5xx failures but not normal 4xx responses", () => {
    expect(retryArchiveRequest(0, new Error("network"))).toBe(true);
    expect(retryArchiveRequest(0, new ApiRequestError(503))).toBe(true);
    expect(retryArchiveRequest(0, new ApiRequestError(404))).toBe(false);
    expect(retryArchiveRequest(2, new Error("network"))).toBe(false);
  });

  it("uses the show-list query key independently", () => {
    const transport: ApiTransport = { requestPage: vi.fn() };
    expect(showsQueryOptions(transport).queryKey).toEqual(["shows"]);
  });
});
