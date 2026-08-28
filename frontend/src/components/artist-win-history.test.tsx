import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Win } from "@/lib/api";
import { ArtistWinHistory } from "./artist-win-history";

function win(id: number): Win {
  return { id, date: `2025-01-0${id}`, show: { id: 1, slug: "music-bank", name: "Music Bank", active: true }, song: { id, title: `Song ${id}`, artist: { id: 1, name: "Artist" }, total_wins: 1 } };
}

describe("ArtistWinHistory", () => {
  it("renders every win without a disclosure control", () => {
    const html = renderToStaticMarkup(<ArtistWinHistory wins={[win(1), win(2), win(3)]} />);
    expect(html.match(/<article/g)).toHaveLength(3);
    expect(html).not.toContain("<details");
    expect(html).not.toContain("Show earlier wins");
  });
});
