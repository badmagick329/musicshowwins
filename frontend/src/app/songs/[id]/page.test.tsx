import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Song, Win } from "@/lib/api-shared";

const apiMocks = vi.hoisted(() => ({
  getSong: vi.fn(),
  getAllSongWins: vi.fn(),
}));

const notFoundMock = vi.hoisted(() => vi.fn(() => {
  throw new Error("NEXT_NOT_FOUND");
}));

vi.mock("next/navigation", () => ({ notFound: notFoundMock }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...apiMocks,
}));

import SongPage, { generateMetadata } from "./page";
import { ApiRequestError } from "@/lib/api";

const song: Song = {
  id: 7,
  title: "Supernova",
  artist: { id: 3, slug: "aespa", name: "aespa" },
  total_wins: 3,
  latest_win_date: "2024-06-02",
  winning_shows: 2,
};

function win(id: number, date: string, show: { id: number; slug: string; name: string }): Win {
  return {
    id,
    date,
    show: { ...show, active: true },
    song,
    performed: null, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 },
  };
}

const wins = [
  win(3, "2024-06-02", { id: 2, slug: "inkigayo", name: "Inkigayo" }),
  win(2, "2024-05-31", { id: 1, slug: "music-bank", name: "Music Bank" }),
  win(1, "2024-05-24", { id: 1, slug: "music-bank", name: "Music Bank" }),
];

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getSong.mockResolvedValue(song);
  apiMocks.getAllSongWins.mockResolvedValue(wins);
});

describe("Song detail page", () => {
  it("renders the summary, show breakdown, metadata, and complete newest-first history", async () => {
    const html = renderToStaticMarkup(await SongPage({ params: Promise.resolve({ id: "7" }) }));
    expect(html).toContain("Supernova");
    expect(html).toContain('href="/artists/aespa"');
    expect(html).toContain("Shows with wins");
    expect(html).toContain("24 May 2024");
    expect(html).toContain("02 Jun 2024");
    expect(html.match(/<article/g)).toHaveLength(3);
    const history = html.slice(html.indexOf("Win history"));
    expect(history.indexOf("02 Jun 2024")).toBeLessThan(history.indexOf("31 May 2024"));
    expect(history.indexOf("31 May 2024")).toBeLessThan(history.indexOf("24 May 2024"));
    expect(apiMocks.getAllSongWins).toHaveBeenCalledWith(7);

    await expect(generateMetadata({ params: Promise.resolve({ id: "7" }) })).resolves.toMatchObject({
      title: "Supernova by aespa: 3 Music Show Wins",
      description: "Supernova by aespa has 3 recorded music-show wins across 2 shows. Earliest recorded win: Music Bank, 24 May 2024. Latest: 02 Jun 2024.",
    });
  });

  it("links the recording to its artist entity in structured data", async () => {
    const html = renderToStaticMarkup(await SongPage({ params: Promise.resolve({ id: "7" }) }));
    const graphs = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((match) => JSON.parse(match[1]));
    expect(graphs.find((graph) => graph["@type"] === "MusicRecording")).toMatchObject({
      "@id": "https://kpopwins.info/songs/7#song",
      name: "Supernova",
      description: (await generateMetadata({ params: Promise.resolve({ id: "7" }) })).description,
      byArtist: { "@id": "https://kpopwins.info/artists/aespa#artist", name: "aespa", url: "https://kpopwins.info/artists/aespa" },
    });
  });

  it("uses the not-found page for invalid and missing song IDs", async () => {
    await expect(SongPage({ params: Promise.resolve({ id: "nope" }) })).rejects.toThrow("NEXT_NOT_FOUND");
    expect(apiMocks.getSong).not.toHaveBeenCalled();

    apiMocks.getSong.mockRejectedValueOnce(new ApiRequestError(404));
    await expect(SongPage({ params: Promise.resolve({ id: "999999" }) })).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFoundMock).toHaveBeenCalledTimes(2);
  });
});
