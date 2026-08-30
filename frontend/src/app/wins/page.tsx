import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { WinsExplorer } from "@/components/wins-explorer";
import { makeQueryClient } from "@/lib/query-client";
import { serverTransport } from "@/lib/api-server";
import { parseWinsFilters, type WinsSearchParams } from "@/lib/wins-filters";
import { showsQueryOptions, winsQueryOptions } from "@/lib/wins-queries";

export const metadata = { title: "Browse wins — KpopWins", description: "Browse every dated K-pop music-show win in the archive." };

export default async function WinsPage({ searchParams }: { searchParams: Promise<WinsSearchParams> }) {
  const filters = parseWinsFilters(await searchParams);
  const queryClient = makeQueryClient();
  await Promise.all([
    queryClient.prefetchQuery(winsQueryOptions(filters, serverTransport)),
    queryClient.prefetchQuery(showsQueryOptions(serverTransport)),
  ]);

  return <HydrationBoundary state={dehydrate(queryClient)}><WinsExplorer /></HydrationBoundary>;
}
