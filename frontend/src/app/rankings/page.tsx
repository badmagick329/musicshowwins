import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { RankingsExplorer } from "@/components/rankings-explorer";
import { QueryProvider } from "@/components/query-provider";
import { makeQueryClient } from "@/lib/query-client";
import { serverTransport } from "@/lib/api-server";
import { archiveToday, parseRankingSelection, type RankingSearchParams, type RankingSelection } from "@/lib/rankings";
import { rankingsQueryOptions } from "@/lib/rankings-queries";
import { noIndexFollow, pageMetadata, paginatedTitle } from "@/lib/seo";

const description = "Rank songs and artists by music-show wins earned in a year, across all time, or within custom dates.";

export async function generateMetadata({ searchParams }: { searchParams: Promise<RankingSearchParams> }): Promise<Metadata> {
  const today = archiveToday();
  const selection = parseRankingSelection(await searchParams, today);
  const canonical = !selection.error && selection.kind === "songs" && selection.period === "year" && selection.year === Number(today.slice(0, 4)) && selection.page === 1;
  return {
    ...pageMetadata({ title: selection.error ? "Music Show Rankings" : paginatedTitle(`Music Show Rankings: ${rankingTitle(selection)}`, selection.page), description, path: "/rankings" }),
    robots: canonical ? undefined : noIndexFollow,
  };
}

function rankingTitle(selection: RankingSelection) {
  const subject = selection.kind === "songs" ? "Top Songs" : "Top Artists";
  if (selection.period === "all-time") return `${subject} of All Time`;
  if (selection.period === "custom") return `${subject}, ${selection.dateFrom} to ${selection.dateTo}`;
  return `${subject} of ${selection.year}`;
}

export default async function RankingsPage({ searchParams }: { searchParams: Promise<RankingSearchParams> }) {
  const today = archiveToday();
  const selection = parseRankingSelection(await searchParams, today);
  const queryClient = makeQueryClient();
  if (!selection.error) await queryClient.prefetchQuery(rankingsQueryOptions(selection, today, serverTransport));
  return <QueryProvider><HydrationBoundary state={dehydrate(queryClient)}><RankingsExplorer today={today} /></HydrationBoundary></QueryProvider>;
}
