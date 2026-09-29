import { renderToStaticMarkup } from "react-dom/server";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { SongResults } from "./song-results";

vi.mock("next/link", () => ({
  default: ({ prefetch, ...props }: ComponentProps<"a"> & { prefetch?: boolean }) => <a {...props} data-prefetch={String(prefetch)} />,
}));

describe("SongResults", () => {
  it("renders each song once with its facts and canonical links", () => {
    const html = renderToStaticMarkup(<SongResults songs={[{ id: 7, title: "Supernova", artist: { id: 3, slug: "aespa", name: "aespa" }, total_wins: 5, latest_win_date: "2024-06-02", winning_shows: 3 }]} empty="None" />);
    expect(html.match(/href="\/songs\/7"/g)).toHaveLength(1);
    expect(html.match(/href="\/artists\/aespa"/g)).toHaveLength(1);
    expect(html.match(/data-prefetch="false"/g)).toHaveLength(2);
    expect(html.match(/Supernova/g)).toHaveLength(1);
    for (const heading of ["Song", "Artist", "Wins", "Latest win", "Shows"]) expect(html).toContain(heading);
    expect(html).toMatch(/<strong>5<\/strong><span class="md:sr-only"> wins<\/span>/);
    expect(html).toContain("02 Jun 2024");
    expect(html).not.toContain("mobile-record");
  });
});
