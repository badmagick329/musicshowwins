import type { Metadata } from "next";

export const siteUrl = "https://kpopwins.info";
export const siteName = "KpopWins";
// Title convention, kept uniform so search results read as one site: Title Case,
// subject first, ": " before a qualifier, " (Page N)" for pagination, and the
// brand suffix added only by the root layout template.
export const homeTitle = "K-pop Music Show Wins This Week & Artist Rankings";
export const siteDescription = "Every K-pop music show win since 2014 from Inkigayo, Music Bank, M Countdown and more, with artist and song rankings.";

export function pageMetadata({ title, description, path }: { title: string; description: string; path: string }): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: "website", url: path, siteName, title, description },
    twitter: { card: "summary_large_image", title, description },
  };
}

export function paginatedTitle(title: string, page: number) {
  return page > 1 ? `${title} (Page ${page})` : title;
}

export function plural(count: number, noun: string) {
  return count === 1 ? noun : `${noun}s`;
}

export const noIndexFollow: Metadata["robots"] = { index: false, follow: true };
