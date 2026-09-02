import type { MetadataRoute } from "next";
import { buildServerApiUrl } from "@/lib/api-server";
import { siteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";
const refreshSeconds = 86_400;

type SitemapEntry = { id: number; latest_win_date: string | null };
type SitemapSource = { artists: SitemapEntry[]; songs: SitemapEntry[] };

function isSitemapSource(value: unknown): value is SitemapSource {
  if (!value || typeof value !== "object") return false;
  const source = value as Record<string, unknown>;
  const validEntry = (entry: unknown) => {
    if (!entry || typeof entry !== "object") return false;
    const item = entry as Record<string, unknown>;
    return Number.isInteger(item.id) &&
      (item.latest_win_date === null || typeof item.latest_win_date === "string");
  };
  return Array.isArray(source.artists) && source.artists.every(validEntry) &&
    Array.isArray(source.songs) && source.songs.every(validEntry);
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

  const response = await fetch(buildServerApiUrl("/sitemap"), {
    headers: { "X-Forwarded-Proto": "https" },
    next: { revalidate: refreshSeconds },
  });
  if (!response.ok) throw new Error(`Sitemap source failed (${response.status}).`);
  const source: unknown = await response.json();
  if (!isSitemapSource(source)) throw new Error("Sitemap source returned invalid data.");

  return [
    ...staticPages,
    ...source.artists.map((artist) => ({
      url: `${siteUrl}/artists/${artist.id}`,
      lastModified: modified(artist.latest_win_date),
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
    ...source.songs.map((song) => ({
      url: `${siteUrl}/songs/${song.id}`,
      lastModified: modified(song.latest_win_date),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    })),
  ];
}
