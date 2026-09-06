import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Artist, Win, WinReference } from "@/lib/api-shared";

const apiMocks = vi.hoisted(() => ({ getArtist: vi.fn(), getAllArtistSongs: vi.fn(), getAllArtistWins: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()), ...apiMocks,
}));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("NEXT_NOT_FOUND"); } }));

import ArtistPage, { generateMetadata } from "./page";

const artist: Artist = { id: 3, name: "aespa", total_wins: 2, winning_songs: 2, latest_win_date: "2024-06-02" };
const earliest: Win = {
  id: 1, date: "2021-01-17", show: { id: 1, slug: "inkigayo", name: "Inkigayo", active: true },
  song: { id: 7, title: "Black Mamba", artist, total_wins: 1, latest_win_date: "2021-01-17", winning_shows: 1 }, references: [],
};
const latest: Win = { ...earliest, id: 2, date: "2024-06-02", song: { ...earliest.song, id: 8, title: "Supernova" } };
const params = Promise.resolve({ id: "3" });

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getArtist.mockResolvedValue(artist);
  apiMocks.getAllArtistSongs.mockResolvedValue([latest.song, earliest.song]);
  apiMocks.getAllArtistWins.mockResolvedValue([latest, earliest]);
});

describe("artist summary and metadata", () => {
  it("server-renders the earliest song link, show and date from full history, independent of URL filters", async () => {
    const props = { params, searchParams: Promise.resolve({ song: "8", show: "music-bank", year: "2024", search: "Supernova" }) };
    const html = renderToStaticMarkup(await ArtistPage(props));
    const summary = html.slice(html.indexOf('<dl'), html.indexOf('</dl>'));
    expect(summary).toContain("Earliest recorded win");
    expect(summary).not.toContain(">First win<");
    expect(summary).toContain('href="/songs/7"');
    expect(summary).toContain("Black Mamba");
    expect(summary).toContain("Inkigayo");
    expect(summary).toContain('<time dateTime="2021-01-17">17 Jan 2021</time>');
    expect(apiMocks.getAllArtistWins).toHaveBeenCalledWith(3);
    expect(html).toBe(renderToStaticMarkup(await ArtistPage({ params })));
  });

  it.each([null, "2026-09-06T00:00:00Z"])("does not treat a published moment or reference verification (%s) as career-first verification", async (lastVerified) => {
    const reference: WinReference = { id: 1, reference_type: "article", provider: "example", external_id: "", url: "https://example.com/story", title: "First-ever trophy", publisher_name: "Example", is_official: true, published_at: null, last_verified_at: lastVerified };
    apiMocks.getAllArtistWins.mockResolvedValue([
      { ...latest, moment: { heading: "A later story", body: "Supporting story", citations: [reference] } },
      { ...earliest, references: [reference], moment: { heading: "First-ever trophy", body: "A career-first story", citations: [reference] } },
    ]);
    const html = renderToStaticMarkup(await ArtistPage({ params }));
    expect(html).toContain("Earliest recorded win");
    expect(html).toContain("Notable moments");
    expect(html).toContain("A career-first story");
    const metadata = await generateMetadata({ params });
    expect(metadata.description).not.toMatch(/\b(first|story|trophy)\b/i);
  });

  it.each([[2, 2, "2 recorded music-show wins across 2 songs"], [1, 1, "1 recorded music-show win across 1 song"], [0, 0, "0 recorded music-show wins across 0 songs"]])("shares factual metadata across search and social fields (%i wins)", async (total, songs, phrase) => {
    apiMocks.getArtist.mockResolvedValue({ ...artist, total_wins: total, winning_songs: songs });
    const metadata = await generateMetadata({ params });
    expect(metadata.description).toContain(phrase);
    expect(metadata.description).not.toContain("complete");
    expect(metadata.openGraph?.description).toBe(metadata.description);
    expect(metadata.twitter?.description).toBe(metadata.description);
    expect(metadata.alternates?.canonical).toBe("/artists/3");
  });

  it("handles an empty catalogue without inventing an earliest win", async () => {
    apiMocks.getAllArtistWins.mockResolvedValue([]);
    const html = renderToStaticMarkup(await ArtistPage({ params }));
    expect(html).toContain("Earliest recorded win");
    expect(html).toContain("Not recorded");
  });
});
