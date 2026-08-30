import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ArtistResults } from "./artist-results";

describe("ArtistResults", () => {
  it("renders a semantic desktop table and linked stacked mobile record", () => {
    const html = renderToStaticMarkup(<ArtistResults artists={[{ id: 3, name: "aespa", total_wins: 12, winning_songs: 4, latest_win_date: "2024-06-02" }]} empty="None" />);

    expect(html).toContain("<table");
    for (const heading of ["Artist", "Wins", "Winning songs", "Latest win"]) expect(html).toContain(heading);
    expect(html).not.toContain("View details");
    expect(html).not.toContain("lucide-arrow-right");
    expect(html).toContain('href="/artists/3"');
    expect(html).toContain("after:absolute after:inset-0");
    expect(html).toContain("mobile-record");
    expect(html).toMatch(/<strong>12<\/strong> wins/);
  });
});
