import { renderToStaticMarkup } from "react-dom/server";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { SongResults } from "./song-results";

vi.mock("next/link", () => ({
  default: ({ prefetch, ...props }: ComponentProps<"a"> & { prefetch?: boolean }) => <a {...props} data-prefetch={String(prefetch)} />,
}));

describe("SongResults", () => {
  it("renders a semantic desktop table and linked stacked mobile record", () => {
    const html = renderToStaticMarkup(<SongResults songs={[{ id: 7, title: "Supernova", artist: { id: 3, name: "aespa" }, total_wins: 5, latest_win_date: "2024-06-02", winning_shows: 3 }]} empty="None" />);
    expect(html).toContain('href="/songs/7"');
    expect(html.match(/data-prefetch="false"/g)).toHaveLength(3);
    expect(html).toContain("<table");
    for (const heading of ["Song", "Artist", "Wins", "Latest win", "Shows"]) expect(html).toContain(heading);
    expect(html).not.toContain("View details");
    expect(html).not.toContain("lucide-arrow-right");
    expect(html).toContain("mobile-record");
    expect(html).toContain("Supernova");
    expect(html).toContain("aespa");
    expect(html).toContain("5");
    expect(html).toContain("Latest");
    expect(html).toContain("3");
  });
});
