import type { Metadata } from "next";

export const siteUrl = "https://kpopwins.info";
export const siteName = "KpopWins";
export const siteDescription = "Explore K-pop music show win counts for BTS, TWICE, EXO and more, with artist rankings and results from Inkigayo, Music Bank and other shows.";

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
