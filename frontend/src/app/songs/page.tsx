import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { SongsExplorer } from "@/components/songs-explorer";
import { serverTransport } from "@/lib/api-server";
import { makeQueryClient } from "@/lib/query-client";
import { parseSongFilters, type SongSearchParams } from "@/lib/song-list";
import { songsQueryOptions } from "@/lib/song-queries";

export const metadata = { title: "Songs", description: "Find songs that won on K-pop music shows and see each song's artist and win history." };

export default async function SongsPage({ searchParams }: { searchParams: Promise<SongSearchParams> }) {
  const filters = parseSongFilters(await searchParams);
  const queryClient = makeQueryClient();
  await queryClient.prefetchQuery(songsQueryOptions(filters, serverTransport));
  return <HydrationBoundary state={dehydrate(queryClient)}><SongsExplorer /></HydrationBoundary>;
}
