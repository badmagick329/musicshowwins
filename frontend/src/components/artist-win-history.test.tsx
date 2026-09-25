import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Win } from "@/lib/api-shared";
import { ArtistWinHistory } from "./artist-win-history";

function win(id: number): Win {
  return { id, date: `2025-01-0${id}`, show: { id: 1, slug: "music-bank", name: "Music Bank", active: true }, song: { id, title: `Song ${id}`, artist: { id: 1, name: "Artist" }, total_wins: 1, latest_win_date: "2025-01-01", winning_shows: 1 }, performed: null, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 } };
}

describe("ArtistWinHistory", () => {
  it("renders every win without a disclosure control", () => {
    const html = renderToStaticMarkup(<ArtistWinHistory wins={[win(1), win(2), win(3)]} />);
    expect(html.match(/<article/g)).toHaveLength(3);
    expect(html).toContain("<table");
    for (const heading of ["Date", "Song", "Music show"]) expect(html).toContain(heading);
    expect(html).toContain('href="/songs/1"');
    expect(html).not.toContain("<details");
    expect(html).not.toContain("Show earlier wins");
  });

  it("tags only notable wins, once per layout", () => {
    const crown = { ...win(2), milestones: { song_win: 5, song_show_win: 3, artist_win: 7 } };
    for (const hideSong of [false, true]) {
      const html = renderToStaticMarkup(<ArtistWinHistory wins={[win(1), crown, win(3)]} hideSong={hideSong} />);
      // One tag in the desktop table and one in the mobile records.
      expect(html.match(/Triple crown · Music Bank/g)).toHaveLength(2);
    }
  });

  it("supports a song-specific empty state", () => {
    const html = renderToStaticMarkup(<ArtistWinHistory wins={[]} emptyMessage="No wins with dates are recorded for this song." />);
    expect(html).toContain("No wins with dates are recorded for this song.");
  });
});
