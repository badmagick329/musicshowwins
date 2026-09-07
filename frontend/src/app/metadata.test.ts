import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getArtist: vi.fn(),
  getSong: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...apiMocks,
}));

import { ApiRequestError } from "@/lib/api";
import { metadata as rootMetadata } from "./layout";
import { generateMetadata as artistsMetadata } from "./artists/page";
import { generateMetadata as songsMetadata } from "./songs/page";
import { generateMetadata as winsMetadata } from "./wins/page";
import { metadata as showsMetadata } from "./shows/page";
import { metadata as aboutMetadata } from "./about/page";
import { generateMetadata as homeMetadata } from "./page";
import { generateMetadata as artistMetadata } from "./artists/[id]/page";
import { generateMetadata as songMetadata } from "./songs/[id]/page";

const staticRoutes = [
  [showsMetadata, "Music Shows", "See the latest winner and full results for each of the six weekly shows covered by KpopWins."],
  [aboutMetadata, "About", "KpopWins records K-pop music show wins from 2014 onward. Share feedback and suggestions for the archive."],
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getArtist.mockResolvedValue({ id: 3, name: "aespa", total_wins: 12, winning_songs: 3 });
  apiMocks.getSong.mockResolvedValue({ id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 3 });
});

describe("page metadata", () => {
  it("uses the required root title and description", () => {
    expect(rootMetadata.title).toEqual({
      default: "K-pop Music Show Wins & Artist Rankings | KpopWins",
      template: "%s | KpopWins",
    });
    expect(rootMetadata.description).toBe("Explore K-pop music show win counts for BTS, TWICE, EXO and more, with artist rankings and results from Inkigayo, Music Bank and other shows.");
    expect(rootMetadata.openGraph).toMatchObject({
      title: "K-pop Music Show Wins & Artist Rankings | KpopWins",
      description: rootMetadata.description,
      url: "/",
    });
    expect(rootMetadata.twitter).toMatchObject({
      title: "K-pop Music Show Wins & Artist Rankings | KpopWins",
      description: rootMetadata.description,
    });
    expect(JSON.stringify(rootMetadata)).not.toContain("clearly kept");
  });

  it.each(staticRoutes)("sets the page title and description without adding the brand", (metadata, title, description) => {
    expect(metadata.title).toBe(title);
    expect(metadata.description).toBe(description);
    expect(String(metadata.title)).not.toContain("KpopWins");
  });

  it("sets canonical metadata and indexing rules for collection pages", async () => {
    const artists = await artistsMetadata({ searchParams: Promise.resolve({}) });
    const songs = await songsMetadata({ searchParams: Promise.resolve({}) });
    const wins = await winsMetadata({ searchParams: Promise.resolve({}) });
    expect(artists).toMatchObject({ title: "Artists", alternates: { canonical: "/artists" } });
    expect(songs).toMatchObject({ title: "Songs", alternates: { canonical: "/songs" } });
    expect(wins).toMatchObject({ title: "Music Show Wins", alternates: { canonical: "/wins" } });

    await expect(artistsMetadata({ searchParams: Promise.resolve({ search: "aespa" }) })).resolves.toMatchObject({ robots: { index: false, follow: true } });
    await expect(songsMetadata({ searchParams: Promise.resolve({ sort: "title" }) })).resolves.toMatchObject({ robots: { index: false, follow: true } });
    await expect(winsMetadata({ searchParams: Promise.resolve({ show: "inkigayo" }) })).resolves.toMatchObject({ robots: { index: false, follow: true } });
  });

  it("keeps the homepage canonical and search-result pages out of the index", async () => {
    await expect(homeMetadata({ searchParams: Promise.resolve({}) })).resolves.toMatchObject({ alternates: { canonical: "/" } });
    await expect(homeMetadata({ searchParams: Promise.resolve({ search: "aespa" }) })).resolves.toMatchObject({
      alternates: { canonical: "/" },
      robots: { index: false, follow: true },
    });
  });

  it("sets artist and song detail titles without duplicate branding", async () => {
    const artist = await artistMetadata({ params: Promise.resolve({ id: "3" }) });
    const song = await songMetadata({ params: Promise.resolve({ id: "7" }) });
    expect(artist).toMatchObject({
      title: "aespa Music Show Wins",
      description: "Explore aespa's 12 recorded music-show wins across 3 songs, with totals by song and show and a dated win history.",
      alternates: { canonical: "/artists/3" },
    });
    expect(song).toMatchObject({
      title: "Supernova by aespa — Music Show Wins",
      description: "Supernova by aespa has 3 recorded music-show wins. See win dates and a breakdown by show.",
      alternates: { canonical: "/songs/7" },
    });

    const template = (rootMetadata.title as { template: string }).template;
    for (const title of ["Artists", "Songs", "Music Show Wins", ...staticRoutes.map(([, value]) => value), artist.title, song.title]) {
      const rendered = template.replace("%s", String(title));
      expect(rendered.match(/KpopWins/g)).toHaveLength(1);
    }
  });

  it("uses clear not-found title fallbacks", async () => {
    await expect(artistMetadata({ params: Promise.resolve({ id: "invalid" }) })).resolves.toMatchObject({ title: "Artist not found" });
    await expect(songMetadata({ params: Promise.resolve({ id: "invalid" }) })).resolves.toMatchObject({ title: "Song not found" });

    apiMocks.getArtist.mockRejectedValueOnce(new ApiRequestError(404));
    apiMocks.getSong.mockRejectedValueOnce(new ApiRequestError(404));
    await expect(artistMetadata({ params: Promise.resolve({ id: "999" }) })).resolves.toMatchObject({ title: "Artist not found" });
    await expect(songMetadata({ params: Promise.resolve({ id: "999" }) })).resolves.toMatchObject({ title: "Song not found" });
  });

  it("does not turn temporary API failures into noindex metadata", async () => {
    apiMocks.getArtist.mockRejectedValueOnce(new ApiRequestError(503));
    apiMocks.getSong.mockRejectedValueOnce(new ApiRequestError(503));
    await expect(artistMetadata({ params: Promise.resolve({ id: "3" }) })).rejects.toThrow();
    await expect(songMetadata({ params: Promise.resolve({ id: "7" }) })).rejects.toThrow();
  });
});
