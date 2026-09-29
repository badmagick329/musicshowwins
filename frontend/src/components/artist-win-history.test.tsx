import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Win } from "@/lib/api-shared";
import { ArtistWinHistory } from "./artist-win-history";

function win(id: number): Win {
  return { id, date: `2025-01-0${id}`, show: { id: 1, slug: "music-bank", name: "Music Bank", active: true }, song: { id, title: `Song ${id}`, artist: { id: 1, slug: "artist", name: "Artist" }, total_wins: 1, latest_win_date: "2025-01-01", winning_shows: 1 }, performed: null, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 } };
}

describe("ArtistWinHistory", () => {
  it("renders every win exactly once for all screen sizes", () => {
    const html = renderToStaticMarkup(<ArtistWinHistory wins={[win(1), win(2), win(3)]} />);
    expect(html.match(/<article/g)).toHaveLength(3);
    expect(html).not.toContain("<table");
    for (const heading of ["Date", "Song", "Music show"]) expect(html).toContain(heading);
    expect(html.match(/href="\/songs\/1"/g)).toHaveLength(1);
    expect(html.match(/datetime="2025-01-01"/gi)).toHaveLength(1);
    expect(html.match(/id="win-1"/g)).toHaveLength(1);
    expect(html).not.toContain("win-mobile-");
    expect(html).not.toContain("<details");
  });

  it("tags only notable wins", () => {
    const crown = { ...win(2), milestones: { song_win: 5, song_show_win: 3, artist_win: 7 } };
    for (const hideSong of [false, true]) {
      const html = renderToStaticMarkup(<ArtistWinHistory wins={[win(1), crown, win(3)]} hideSong={hideSong} />);
      expect(html.match(/Triple crown · Music Bank/g)).toHaveLength(1);
    }
  });

  it("supports a song-specific empty state", () => {
    const html = renderToStaticMarkup(<ArtistWinHistory wins={[]} emptyMessage="No wins with dates are recorded for this song." />);
    expect(html).toContain("No wins with dates are recorded for this song.");
  });
});
