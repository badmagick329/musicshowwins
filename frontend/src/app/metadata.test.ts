import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getArtist: vi.fn(),
  getSong: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...apiMocks,
}));

import { metadata as rootMetadata } from "./layout";
import { metadata as artistsMetadata } from "./artists/page";
import { metadata as songsMetadata } from "./songs/page";
import { metadata as winsMetadata } from "./wins/page";
import { metadata as showsMetadata } from "./shows/page";
import { metadata as aboutMetadata } from "./about/page";
import { generateMetadata as artistMetadata } from "./artists/[id]/page";
import { generateMetadata as songMetadata } from "./songs/[id]/page";

const staticRoutes = [
  [artistsMetadata, "Artists", "Find artists by name or win total, then view their songs and full win history."],
  [songsMetadata, "Songs", "Find songs that won on K-pop music shows and see each song's artist and win history."],
  [winsMetadata, "Music Show Wins", "Search K-pop music show results by artist, song, show, year, or date. Coverage starts in 2014."],
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
  });

  it.each(staticRoutes)("sets the page title and description without adding the brand", (metadata, title, description) => {
    expect(metadata.title).toBe(title);
    expect(metadata.description).toBe(description);
    expect(String(metadata.title)).not.toContain("KpopWins");
  });

  it("sets artist and song detail titles without duplicate branding", async () => {
    const artist = await artistMetadata({ params: Promise.resolve({ id: "3" }) });
    const song = await songMetadata({ params: Promise.resolve({ id: "7" }) });
    expect(artist).toEqual({
      title: "aespa Music Show Wins",
      description: "See aespa's winning songs and complete music show win history.",
    });
    expect(song).toEqual({
      title: "Supernova by aespa",
      description: "See every recorded music show win for Supernova by aespa.",
    });

    const template = (rootMetadata.title as { template: string }).template;
    for (const title of [...staticRoutes.map(([, value]) => value), artist.title, song.title]) {
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
