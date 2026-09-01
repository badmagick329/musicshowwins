import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Leaderboard, MusicShowList, RecentWins, ShowBadge } from "./data-display";

describe("ShowBadge", () => {
  it("keeps the accessible show name and stable colour class without a decorative dot", () => {
    const html = renderToStaticMarkup(<ShowBadge slug="music-bank" name="Music Bank" />);
    expect(html).toContain("Music Bank");
    expect(html).toContain("show-music-bank");
    expect(html).not.toContain("show-dot");
    expect(html).not.toContain("aria-hidden");
  });
});

describe("MusicShowList", () => {
  it("links each homepage show card to its filtered wins", () => {
    const html = renderToStaticMarkup(<MusicShowList shows={[{ id: 1, slug: "music-core", name: "Show! Music Core", active: true, total_wins: 470, first_win_date: "2014-01-01", latest_win_date: "2026-08-01", latest_win: null }]} />);
    expect(html).toContain('href="/wins?show=music-core#wins-results-title"');
    expect(html).toContain('aria-label="View Show! Music Core wins"');
  });
});

describe("homepage data tables", () => {
  it("renders semantic desktop tables alongside mobile records", () => {
    const leaderboard = renderToStaticMarkup(<Leaderboard kind="artist" rows={[{ rank: 1, wins: 12, artist: { id: 3, name: "aespa" } }]} />);
    const recent = renderToStaticMarkup(<RecentWins wins={[{ id: 1, date: "2024-06-02", show: { id: 1, slug: "music-bank", name: "Music Bank", active: true }, song: { id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 1, latest_win_date: "2024-06-02", winning_shows: 1 }, references: [] }]} />);

    expect(leaderboard).toContain("Top five artists by music show wins");
    expect(leaderboard).toContain("rank-marker--1");
    expect(recent).toContain("Most recent music show wins");
    for (const heading of ["Date", "Song", "Artist", "Music show", "Video"]) expect(recent).toContain(heading);
    expect(recent).toContain("mobile-record");
  });
});
