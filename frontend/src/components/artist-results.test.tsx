import { renderToStaticMarkup } from "react-dom/server";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { ArtistResults } from "./artist-results";

vi.mock("next/link", () => ({
  default: ({ prefetch, ...props }: ComponentProps<"a"> & { prefetch?: boolean }) => <a {...props} data-prefetch={String(prefetch)} />,
}));

describe("ArtistResults", () => {
  it("renders each artist once as a whole-row link", () => {
    const html = renderToStaticMarkup(<ArtistResults artists={[{ id: 3, slug: "aespa", name: "aespa", total_wins: 12, winning_songs: 4, latest_win_date: "2024-06-02" }]} empty="None" />);

    for (const heading of ["Artist", "Wins", "Winning songs", "Latest win"]) expect(html).toContain(heading);
    expect(html.match(/href="\/artists\/aespa"/g)).toHaveLength(1);
    expect(html.match(/data-prefetch="false"/g)).toHaveLength(1);
    expect(html).toContain("after:absolute after:inset-0");
    expect(html).toMatch(/<strong>12<\/strong><span class="md:sr-only"> wins<\/span>/);
    expect(html).not.toContain("mobile-record");
  });
});
