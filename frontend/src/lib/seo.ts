import type { Metadata } from "next";

export const siteUrl = "https://kpopwins.info";
export const siteName = "KpopWins";
export const siteDescription = "Search K-pop music show wins by artist, song, show, or date. Coverage starts in 2014.";

export function pageMetadata({ title, description, path }: { title: string; description: string; path: string }): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: "website", url: path, siteName, title, description },
    twitter: { card: "summary_large_image", title, description },
  };
}

export const noIndexFollow: Metadata["robots"] = { index: false, follow: true };
