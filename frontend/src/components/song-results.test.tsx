import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SongResults } from "./song-results";

describe("SongResults", () => {
  it("makes every result row a song-detail link with the complete song facts", () => {
    const html = renderToStaticMarkup(<SongResults songs={[{ id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 5, latest_win_date: "2024-06-02", winning_shows: 3 }]} empty="None" />);
    expect(html).toContain('href="/songs/7"');
    expect(html).toContain("Supernova");
    expect(html).toContain("aespa");
    expect(html).toContain("5");
    expect(html).toContain("Latest");
    expect(html).toContain("3");
  });
});
