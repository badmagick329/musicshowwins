import type { Metadata } from "next";
import { ErrorState } from "@/components/data-display";
import { ShowCards } from "@/components/show-cards";
import { getShows } from "@/lib/api";

export const metadata: Metadata = {
  title: "Music Shows — KpopWins",
  description: "Explore the six weekly Korean music shows covered by the KpopWins archive.",
};

export const dynamic = "force-dynamic";

export default async function ShowsPage() {
  let shows: Awaited<ReturnType<typeof getShows>>["results"] = [];
  let failed = false;
  try {
    const response = await getShows();
    shows = response.results;
  } catch {
    failed = true;
  }
  return <ShowsContent shows={shows} failed={failed} />;
}

function ShowsContent({ shows, failed = false }: { shows: Awaited<ReturnType<typeof getShows>>["results"]; failed?: boolean }) {
  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-10 pt-10 lg:px-8 lg:pt-14">
      <header className="max-w-3xl">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">Music shows</h1>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">Explore archive coverage and recent winners across the six weekly Korean music shows tracked by KpopWins.</p>
      </header>
      {failed && <ErrorState messages={["Music shows could not be loaded."]} />}
      <div className="mt-8"><ShowCards shows={shows} /></div>
    </main>
  );
}
