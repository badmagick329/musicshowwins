import type { MetadataRoute } from "next";
import { buildServerApiUrl } from "@/lib/api-server";
import { parseApiPage, type ApiPage, type Artist, type Song } from "@/lib/api-shared";
import { siteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";
const refreshSeconds = 86_400;

async function getAll<T>(path: string, ordering: string) {
  const results: T[] = [];
  let pageNumber = 1;
  while (true) {
    if (pageNumber > 1_000) throw new Error("Sitemap source returned too many pages.");
    const response = await fetch(buildServerApiUrl(path, { ordering, page: pageNumber }), {
      next: { revalidate: refreshSeconds },
    });
    if (!response.ok) throw new Error(`Sitemap source failed (${response.status}).`);
    const page: ApiPage<T> = parseApiPage(await response.json());
    results.push(...page.results);
    if (!page.next) return results;
    pageNumber += 1;
  }
}

function modified(value: string | null) {
  if (!value) return undefined;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${siteUrl}/`, changeFrequency: "daily", priority: 1 },
    { url: `${siteUrl}/artists`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${siteUrl}/songs`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${siteUrl}/wins`, changeFrequency: "daily", priority: 0.9 },
    { url: `${siteUrl}/shows`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${siteUrl}/about`, changeFrequency: "monthly", priority: 0.5 },
  ];

  try {
    const [artists, songs] = await Promise.all([
      getAll<Artist>("/artists", "name"),
      getAll<Song>("/songs", "title,artist__name"),
    ]);
    return [
      ...staticPages,
      ...artists.map((artist) => ({
        url: `${siteUrl}/artists/${artist.id}`,
        lastModified: modified(artist.latest_win_date),
        changeFrequency: "weekly" as const,
        priority: 0.8,
      })),
      ...songs.map((song) => ({
        url: `${siteUrl}/songs/${song.id}`,
        lastModified: modified(song.latest_win_date),
        changeFrequency: "weekly" as const,
        priority: 0.7,
      })),
    ];
  } catch {
    return staticPages;
  }
}
