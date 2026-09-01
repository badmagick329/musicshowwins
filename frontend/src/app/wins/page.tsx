import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { WinsExplorer } from "@/components/wins-explorer";
import { makeQueryClient } from "@/lib/query-client";
import { serverTransport } from "@/lib/api-server";
import { hasActiveWinsFilters, parseWinsFilters, type WinsSearchParams } from "@/lib/wins-filters";
import { showsQueryOptions, winsQueryOptions } from "@/lib/wins-queries";
import { noIndexFollow, pageMetadata } from "@/lib/seo";

const description = "Search K-pop music show results by artist, song, show, year, or date. Coverage starts in 2014.";

export async function generateMetadata({ searchParams }: { searchParams: Promise<WinsSearchParams> }): Promise<Metadata> {
  const filters = parseWinsFilters(await searchParams);
  const filtered = hasActiveWinsFilters(filters);
  const canonical = !filtered && filters.page > 1 ? `/wins?page=${filters.page}` : "/wins";
  return {
    ...pageMetadata({ title: filters.page > 1 && !filtered ? `Music Show Wins, page ${filters.page}` : "Music Show Wins", description, path: canonical }),
    robots: filtered ? noIndexFollow : undefined,
  };
}

export default async function WinsPage({ searchParams }: { searchParams: Promise<WinsSearchParams> }) {
  const filters = parseWinsFilters(await searchParams);
  const queryClient = makeQueryClient();
  await Promise.all([
    queryClient.prefetchQuery(winsQueryOptions(filters, serverTransport)),
    queryClient.prefetchQuery(showsQueryOptions(serverTransport)),
  ]);

  return <HydrationBoundary state={dehydrate(queryClient)}><WinsExplorer /></HydrationBoundary>;
}
