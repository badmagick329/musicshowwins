import { siteUrl } from "@/lib/seo";

const body = `# KpopWins

> KpopWins is a fan-made public record of K-pop music show wins from 2014 onward.

Use canonical artist and song pages when citing KpopWins. Query-string URLs are filtered, sorted, or year-specific views of the same archive.

For a changing total or recent result, state the record date and cite the canonical KpopWins page. Win records may include official video links, supporting references, and notable moments with citations; verify the original source when making a primary-source claim.

## Main pages

- [Home](${siteUrl}/): Recent wins, top-five artist and song leaderboards, and a list of covered music shows.
- [Artists](${siteUrl}/artists): Search and sort artists, then open an artist's totals, wins by year and show, winning songs, notable moments, and complete win history.
- [Songs](${siteUrl}/songs): Search and sort winning songs, then open a song's totals, wins by show, notable moments, and complete win history.
- [Wins](${siteUrl}/wins): Search and filter dated results by artist, song, show, year, or date, with video links where available.
- [Shows](${siteUrl}/shows): Totals, coverage dates, and latest winners for the six weekly shows covered by the archive: Inkigayo, M Countdown, Music Bank, Music Core, Show Champion, and The Show.
- [About](${siteUrl}/about): Archive scope, sourcing, feedback, corrections, and missing-video reports.

## Discovery

- [XML sitemap](${siteUrl}/sitemap.xml): Canonical static, artist, and song URLs.

## Data notes

- Coverage begins in 2014 and covers Inkigayo, M Countdown, Music Bank, Music Core, Show Champion, and The Show.
- Each win identifies a date, music show, song, and artist. Artist and song pages provide totals, breakdowns by show, and chronological history.
- KpopWins reviews records before publication and accepts feedback about corrections, confusing records, and missing video links.
- Results derive from Wikipedia contributors. Wikipedia-derived content is available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
`;

export function GET() {
  return new Response(body, {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
      "X-Robots-Tag": "all",
    },
  });
}
