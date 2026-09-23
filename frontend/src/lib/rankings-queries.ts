import { queryOptions } from "@tanstack/react-query";
import { archiveStaleTime, retryArchiveRequest } from "@/lib/query-client";
import type { ApiPage, ApiTransport, ArtistLeaderboardRow, SongLeaderboardRow } from "@/lib/api-shared";
import { rankingApiParams, type RankingSelection } from "@/lib/rankings";

export function rankingsQueryOptions(selection: RankingSelection, today: string, transport: ApiTransport) {
  const params = rankingApiParams(selection, today);
  return queryOptions<ApiPage<ArtistLeaderboardRow | SongLeaderboardRow> & { selection: RankingSelection }>({
    queryKey: ["rankings", selection.kind, selection.period, params],
    queryFn: async ({ signal }) => {
      const page = selection.kind === "songs"
        ? await transport.requestPage<SongLeaderboardRow>("/leaderboards/songs", params, signal)
        : await transport.requestPage<ArtistLeaderboardRow>("/leaderboards/artists", params, signal);
      return { ...page, selection };
    },
    staleTime: archiveStaleTime,
    retry: retryArchiveRequest,
  });
}
