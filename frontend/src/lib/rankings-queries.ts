import { queryOptions } from "@tanstack/react-query";
import { archiveStaleTime, retryArchiveRequest } from "@/lib/query-client";
import type { ApiPage, ApiTransport, ArtistLeaderboardRow, SongLeaderboardRow } from "@/lib/api-shared";
import { rankingApiParams, type RankingSelection } from "@/lib/rankings";

export function rankingsQueryOptions(selection: RankingSelection, today: string, transport: ApiTransport) {
  const params = rankingApiParams(selection, today);
  return queryOptions<ApiPage<ArtistLeaderboardRow | SongLeaderboardRow>>({
    queryKey: ["rankings", selection.kind, params],
    queryFn: ({ signal }) => selection.kind === "songs"
      ? transport.requestPage<SongLeaderboardRow>("/leaderboards/songs", params, signal)
      : transport.requestPage<ArtistLeaderboardRow>("/leaderboards/artists", params, signal),
    staleTime: archiveStaleTime,
    retry: retryArchiveRequest,
  });
}
