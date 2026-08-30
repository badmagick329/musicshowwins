import { describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import type { ApiTransport } from "./api-shared";
import { defaultSongFilters } from "./song-list";
import { songQueryKeys, songsQueryOptions } from "./song-queries";

describe("song queries", () => {
  it("uses normalized, response-specific keys", () => {
    const defaults = defaultSongFilters();
    expect(songQueryKeys.list(defaults)).toEqual(songQueryKeys.list({ ...defaults, search: "  " }));
    expect(songQueryKeys.list(defaults)).not.toEqual(songQueryKeys.list({ ...defaults, sort: "artist" }));
    expect(songQueryKeys.list(defaults)).not.toEqual(songQueryKeys.list({ ...defaults, page: 2 }));
  });

  it("passes the API parameters and AbortSignal to the transport", async () => {
    const signal = new AbortController().signal;
    const transport: ApiTransport = { requestPage: vi.fn(async () => ({ count: 0, next: null, previous: null, results: [] })) };
    const filters = { search: "ive", sort: "artist" as const, page: 2 };
    const queryFn = songsQueryOptions(filters, transport).queryFn;
    if (!queryFn) throw new Error("Expected songs query function");
    await queryFn({ queryKey: songQueryKeys.list(filters), signal, meta: undefined, client: new QueryClient() });
    expect(transport.requestPage).toHaveBeenCalledWith("/songs", { search: "ive", ordering: "artist__name,title", page: 2 }, signal);
  });
});
