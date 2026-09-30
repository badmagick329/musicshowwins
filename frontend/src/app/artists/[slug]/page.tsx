import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { ArtistWinsByYear } from "@/components/artist-wins-by-year";
import { parseArtistYear } from "@/lib/artist-years";
import { formatDate } from "@/lib/utils";
import { ApiRequestError, getAllArtistWins, getArtist } from "@/lib/api";
import { artistHighlights, debutFact, summarizeArtist, tripleCrowns, type TripleCrown } from "@/lib/artist-profile";
import { JsonLd } from "@/components/json-ld";
import { Metric, MetricGrid } from "@/components/data-display";
import type { ArtistDetail, Win } from "@/lib/api-shared";
import { noIndexFollow, pageMetadata, plural, siteUrl } from "@/lib/seo";
import { artistPath } from "@/lib/paths";
import { artistJsonLd } from "@/lib/structured-data";

// Slugs are lowercase words; digits alone are the IDs older URLs used.
function artistKey(value: string) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) && value !== "0" ? value : null;
}

async function loadArtist(key: string) {
  try { return await getArtist(key); }
  catch (error) { if (error instanceof ApiRequestError && error.status === 404) notFound(); throw error; }
}

// Shared by the meta description and the structured data so both state the same facts.
function artistDescription(artist: ArtistDetail, wins: Win[]) {
  const { earliestWin, latestWin } = summarizeArtist(wins);
  const counts = `${artist.total_wins} recorded music-show ${plural(artist.total_wins, "win")} across ${artist.winning_songs} ${plural(artist.winning_songs, "song")}`;
  const earliestLabel = debutFact(artist, earliestWin)?.kind === "first-win" ? "First win" : "Earliest recorded win";
  const dates = earliestWin && latestWin
    ? ` ${earliestLabel}: ${earliestWin.song.title} on ${earliestWin.show.name}, ${formatDate(earliestWin.date)}. Latest win: ${formatDate(latestWin.date)}.`
    : "";
  return `${artist.name} has ${counts}.${dates}`;
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const key = artistKey((await params).slug);
  if (!key) return { title: "Artist Not Found", description: "The requested artist could not be found in KpopWins.", robots: noIndexFollow };
  try {
    const artist = await getArtist(key);
    const wins = await getAllArtistWins(artist.id);
    return pageMetadata({
      title: `${artist.name} Music Show Wins: ${artist.total_wins} Total`,
      description: artistDescription(artist, wins),
      path: artistPath(artist),
      indexable: artist.indexable,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return { title: "Artist Not Found", description: "The requested artist could not be found in KpopWins.", robots: noIndexFollow };
    throw error;
  }
}

export default async function ArtistPage({ params, searchParams = Promise.resolve({}) }: { params: Promise<{ slug: string }>; searchParams?: Promise<{ year?: string | string[] }> }) {
  const key = artistKey((await params).slug);
  if (!key) notFound();
  const artist = await loadArtist(key);
  const year = (await searchParams).year;
  // Old numeric links and search results move to the name-based URL for good.
  if (key !== artist.slug) permanentRedirect(`${artistPath(artist)}${typeof year === "string" ? `?year=${encodeURIComponent(year)}` : ""}`);
  const wins = await getAllArtistWins(artist.id);
  const summary = summarizeArtist(wins);
  const highlights = artistHighlights(wins);
  const crowns = tripleCrowns(wins);
  const debut = debutFact(artist, summary.earliestWin);

  return (
    <>
      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: siteUrl },
          { "@type": "ListItem", position: 2, name: "Artists", item: `${siteUrl}/artists` },
          { "@type": "ListItem", position: 3, name: artist.name, item: `${siteUrl}${artistPath(artist)}` },
        ],
      }} />
      <JsonLd data={artistJsonLd(artist, wins, artistDescription(artist, wins))} />
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <header className="border-2 bg-surface-berry p-6 text-surface-berry-foreground shadow-[4px_4px_0_var(--section-ink)] sm:p-8">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">{artist.name}</h1><p className="mt-2 text-surface-berry-foreground/75">{summary.totalWins} recorded music show {plural(summary.totalWins, "win")} across {summary.winningSongs} {plural(summary.winningSongs, "song")}</p>
      </header>

      <section className="mt-10" aria-labelledby="summary-title">
        <h2 id="summary-title" className="mb-4 border-b-2 pb-3 font-heading text-2xl font-bold">Win summary</h2>
        {debut && <p className="mb-4 max-w-3xl leading-relaxed">{debut.sentence}</p>}
        <MetricGrid>
          <Metric label="Recorded wins" value={String(summary.totalWins)} />
          <Metric label="Winning songs" value={String(summary.winningSongs)} />
          <Metric label={debut?.kind === "first-win" ? "First win" : "Earliest recorded win"} value={summary.earliestWin ? <WinDetail win={summary.earliestWin} /> : "Not recorded"} />
          <Metric label="Latest win" value={summary.latestWin ? <WinDetail win={summary.latestWin} /> : "Not recorded"} />
        </MetricGrid>
        {highlights.length > 0 && <p className="mt-3 text-sm text-muted-foreground"><strong className="font-semibold text-foreground">Highlights:</strong> {highlights.join(" · ")}</p>}
        {crowns.length > 0 && <TripleCrowns crowns={crowns} />}
      </section>

      <ArtistWinsByYear artist={artist} wins={wins} initialYear={parseArtistYear(year)} />
    </main>
    </>
  );
}

function TripleCrowns({ crowns }: { crowns: TripleCrown[] }) {
  const total = crowns.reduce((sum, crown) => sum + crown.shows.length, 0);
  const label = total > 3 ? `${total} triple crowns` : total === 1 ? "Triple crown" : "Triple crowns";
  return <p className="mt-2 text-sm text-muted-foreground">
    <strong className="font-semibold text-foreground">{label}:</strong>{" "}
    {crowns.map((crown, index) => <span key={crown.song.id}>
      {index > 0 && ", "}
      <Link prefetch={false} href={`/songs/${crown.song.id}`} className="underline underline-offset-4">{crown.song.title}</Link> ({crown.shows.join(", ")})
    </span>)}
  </p>;
}

function WinDetail({ win }: { win: Win }) {
  return <>
    <Link prefetch={false} href={`/songs/${win.song.id}`} className="compact-link-target text-lg leading-snug underline underline-offset-4">{win.song.title}</Link>
    <span className="mt-1 block font-sans text-sm font-normal leading-relaxed">
      {win.show.name}<br />
      <time dateTime={win.date}>{formatDate(win.date)}</time>
    </span>
  </>;
}
