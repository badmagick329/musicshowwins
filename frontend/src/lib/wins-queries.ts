import { queryOptions } from "@tanstack/react-query";
import { archiveStaleTime, retryArchiveRequest } from "@/lib/query-client";
import type { ApiTransport, Show, Win } from "@/lib/api-shared";
import { normalizeWinsFilters, winsApiParams, type WinsFilters } from "@/lib/wins-filters";

export const queryKeys = {
  shows: ["shows"] as const,
  wins: {
    list: (filters: WinsFilters) => ["wins", "list", normalizeWinsFilters(filters)] as const,
  },
};

export function showsQueryOptions(transport: ApiTransport) {
  return queryOptions({
    queryKey: queryKeys.shows,
    queryFn: ({ signal }) => transport.requestPage<Show>("/shows", undefined, signal),
    staleTime: archiveStaleTime,
    retry: retryArchiveRequest,
  });
}

export function winsQueryOptions(filters: WinsFilters, transport: ApiTransport) {
  const normalized = normalizeWinsFilters(filters);
  return queryOptions({
    queryKey: queryKeys.wins.list(normalized),
    queryFn: ({ signal }) => transport.requestPage<Win>("/wins", winsApiParams(normalized), signal),
    staleTime: archiveStaleTime,
    retry: retryArchiveRequest,
  });
}
