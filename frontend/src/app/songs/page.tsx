import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { SongsExplorer } from "@/components/songs-explorer";
import { serverTransport } from "@/lib/api-server";
import { makeQueryClient } from "@/lib/query-client";
import { parseSongFilters, type SongSearchParams } from "@/lib/song-list";
import { songsQueryOptions } from "@/lib/song-queries";
import { noIndexFollow, pageMetadata } from "@/lib/seo";

const description = "Find songs that won on K-pop music shows and see each song's artist and win history.";

export async function generateMetadata({ searchParams }: { searchParams: Promise<SongSearchParams> }): Promise<Metadata> {
  const filters = parseSongFilters(await searchParams);
  const canonical = !filters.search && filters.page > 1 ? `/songs?page=${filters.page}` : "/songs";
  return {
    ...pageMetadata({ title: filters.page > 1 && !filters.search ? `Songs, page ${filters.page}` : "Songs", description, path: canonical }),
    robots: filters.search || filters.sort !== "wins" ? noIndexFollow : undefined,
  };
}

export default async function SongsPage({ searchParams }: { searchParams: Promise<SongSearchParams> }) {
  const filters = parseSongFilters(await searchParams);
  const queryClient = makeQueryClient();
  await queryClient.prefetchQuery(songsQueryOptions(filters, serverTransport));
  return <HydrationBoundary state={dehydrate(queryClient)}><SongsExplorer /></HydrationBoundary>;
}
