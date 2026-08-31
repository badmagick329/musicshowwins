import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getShows } = vi.hoisted(() => ({ getShows: vi.fn() }));
vi.mock("@/lib/api", () => ({ getShows }));

import ShowsPage from "./page";

const show = {
  id: 1,
  slug: "music-bank",
  name: "Music Bank",
  active: true,
  total_wins: 42,
  first_win_date: "2014-01-03",
  latest_win_date: "2025-08-01",
  latest_win: { id: 9, date: "2025-08-01", song: { id: 4, title: "Winner", artist: { id: 3, name: "Example Artist" } } },
};

describe("ShowsPage", () => {
  beforeEach(() => getShows.mockReset());

  it("renders show coverage and archive links", async () => {
    getShows.mockResolvedValue({ count: 1, next: null, previous: null, results: [show] });
    const html = renderToStaticMarkup(await ShowsPage());
    expect(html).toContain("Music Bank");
    expect(html).toContain("42");
    expect(html).toContain('href="/songs/4"');
    expect(html).toContain('href="/artists/3"');
    expect(html).toContain('href="/wins?show=music-bank#wins-results-title"');
    expect(html).toContain("View wins");
    expect(html).toContain("after:absolute after:inset-0");
    expect(html).not.toContain("Active weekly show");
    expect(html).not.toContain("See the latest winner and full results");
  });

  it("renders empty and failure states", async () => {
    getShows.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    expect(renderToStaticMarkup(await ShowsPage())).toContain("Music show information is unavailable");
    getShows.mockImplementationOnce(async () => { throw new Error("offline"); });
    expect(renderToStaticMarkup(await ShowsPage())).toContain("Some results couldn&#x27;t load");
  });
});
