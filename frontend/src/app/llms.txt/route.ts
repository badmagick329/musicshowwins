import { siteUrl } from "@/lib/seo";

const body = `# KpopWins

> KpopWins is a public record of K-pop music show wins from 2014 onward.

Use canonical artist and song pages when citing KpopWins. Query-string URLs are filtered or sorted views of the same archive.

For a changing total or recent result, state the record date and cite the canonical KpopWins page. Follow a win's reference links when a primary source is needed.

## Main pages

- [Home](${siteUrl}/): Recent wins and artist and song leaderboards.
- [Artists](${siteUrl}/artists): Browse artists and open an artist's complete win history.
- [Songs](${siteUrl}/songs): Browse winning songs and open a song's complete win history.
- [Wins](${siteUrl}/wins): Search dated results by artist, song, show, year, or date.
- [Shows](${siteUrl}/shows): The six weekly music shows covered by the archive.
- [About](${siteUrl}/about): Scope, sourcing, and correction process.

## Discovery

- [XML sitemap](${siteUrl}/sitemap.xml): Canonical static, artist, and song URLs.

## Data notes

- Coverage begins in 2014.
- Each win identifies a date, music show, song, and artist.
- KpopWins reviews records before publication and accepts correction reports.
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
