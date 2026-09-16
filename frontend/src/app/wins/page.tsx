import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { WinsExplorer } from "@/components/wins-explorer";
import { QueryProvider } from "@/components/query-provider";
import { makeQueryClient } from "@/lib/query-client";
import { serverTransport } from "@/lib/api-server";
import { ApiRequestError } from "@/lib/api-shared";
import { hasActiveWinsFilters, parseWinsFilters, winsDetailId, winsFilterError, winsUrl, type WinsSearchParams } from "@/lib/wins-filters";
import { selectedArtistQueryOptions, selectedSongQueryOptions, showsQueryOptions, winsQueryOptions } from "@/lib/wins-queries";
import { noIndexFollow, pageMetadata } from "@/lib/seo";

const description = "Search K-pop music show results by artist, song, show, year, or date. Coverage starts in 2014.";

export async function generateMetadata({ searchParams }: { searchParams: Promise<WinsSearchParams> }): Promise<Metadata> {
  const params = await searchParams;
  const filters = parseWinsFilters(params);
  const filtered = hasActiveWinsFilters(filters);
  const canonical = !filtered && filters.page > 1 ? `/wins?page=${filters.page}` : "/wins";
  return {
    ...pageMetadata({ title: filters.page > 1 && !filtered ? `Music Show Wins, page ${filters.page}` : "Music Show Wins", description, path: canonical }),
    robots: filtered || winsFilterError(params) ? noIndexFollow : undefined,
  };
}

export default async function WinsPage({ searchParams }: { searchParams: Promise<WinsSearchParams> }) {
  const params = await searchParams;
  const filters = parseWinsFilters(params);
  const filterError = winsFilterError(params);
  const artistId = winsDetailId(filters.artist);
  const songId = winsDetailId(filters.song);
  const queryClient = makeQueryClient();

  if (!filterError) {
    try {
      await queryClient.fetchQuery(winsQueryOptions(filters, serverTransport));
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 404 && filters.page > 1) {
        redirect(winsUrl({ ...filters, page: 1 }));
      }
    }
  }

  await Promise.all([
    queryClient.prefetchQuery(showsQueryOptions(serverTransport)),
    ...(artistId ? [queryClient.prefetchQuery(selectedArtistQueryOptions(artistId, serverTransport))] : []),
    ...(songId ? [queryClient.prefetchQuery(selectedSongQueryOptions(songId, serverTransport))] : []),
  ]);

  return <QueryProvider><HydrationBoundary state={dehydrate(queryClient)}><WinsExplorer /></HydrationBoundary></QueryProvider>;
}
