import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getArtist: vi.fn(),
  getSong: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...apiMocks,
}));

import { dynamic as rootDynamic, metadata as rootMetadata } from "./layout";
import { generateMetadata as artistsMetadata } from "./artists/page";
import { generateMetadata as songsMetadata } from "./songs/page";
import { generateMetadata as winsMetadata } from "./wins/page";
import { metadata as showsMetadata } from "./shows/page";
import { metadata as aboutMetadata } from "./about/page";
import { generateMetadata as artistMetadata } from "./artists/[id]/page";
import { generateMetadata as songMetadata } from "./songs/[id]/page";

const staticRoutes = [
  [showsMetadata, "Music Shows", "See the latest winner and full results for each of the six weekly shows covered by KpopWins."],
  [aboutMetadata, "About", "KpopWins records K-pop music show wins from 2014 onward. You can also report missing or incorrect results."],
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getArtist.mockResolvedValue({ id: 3, name: "aespa", total_wins: 12 });
  apiMocks.getSong.mockResolvedValue({ id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 3 });
});

describe("page metadata", () => {
  it("uses the required root title and description", () => {
    expect(rootMetadata.title).toEqual({
      default: "KpopWins | K-pop Music Show Wins",
      template: "%s | KpopWins",
    });
    expect(rootMetadata.description).toBe("Search K-pop music show wins by artist, song, show, or date. Coverage starts in 2014.");
    expect(JSON.stringify(rootMetadata)).not.toContain("clearly kept");
    expect(rootDynamic).toBe("force-dynamic");
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

  it("sets artist and song detail titles without duplicate branding", async () => {
    const artist = await artistMetadata({ params: Promise.resolve({ id: "3" }) });
    const song = await songMetadata({ params: Promise.resolve({ id: "7" }) });
    expect(artist).toMatchObject({
      title: "aespa Music Show Wins",
      description: "See aespa's winning songs and complete music show win history.",
      alternates: { canonical: "/artists/3" },
    });
    expect(song).toMatchObject({
      title: "Supernova by aespa",
      description: "See every recorded music show win for Supernova by aespa.",
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

    apiMocks.getArtist.mockRejectedValueOnce(new Error("missing"));
    apiMocks.getSong.mockRejectedValueOnce(new Error("missing"));
    await expect(artistMetadata({ params: Promise.resolve({ id: "999" }) })).resolves.toMatchObject({ title: "Artist not found" });
    await expect(songMetadata({ params: Promise.resolve({ id: "999" }) })).resolves.toMatchObject({ title: "Song not found" });
  });
});
