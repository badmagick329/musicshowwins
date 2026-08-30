import { queryOptions } from "@tanstack/react-query";
import type { ApiTransport, Song } from "@/lib/api-shared";
import { archiveStaleTime, retryArchiveRequest } from "@/lib/query-client";
import { normalizeSongFilters, songApiParams, type SongFilters } from "@/lib/song-list";

export const songQueryKeys = {
  list: (filters: SongFilters) => ["songs", "list", normalizeSongFilters(filters)] as const,
};

export function songsQueryOptions(filters: SongFilters, transport: ApiTransport) {
  const normalized = normalizeSongFilters(filters);
  return queryOptions({
    queryKey: songQueryKeys.list(normalized),
    queryFn: ({ signal }) => transport.requestPage<Song>("/songs", songApiParams(normalized), signal),
    staleTime: archiveStaleTime,
    retry: retryArchiveRequest,
  });
}
