// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WinMoments } from "@/components/win-moments";
import type { Win } from "@/lib/api-shared";

const win: Win = {
  id: 42,
  date: "2017-06-20",
  show: { id: 1, slug: "the-show", name: "The Show", active: true },
  song: { id: 2, title: "What's My Name?", artist: { id: 3, name: "T-ara" }, total_wins: 1, latest_win_date: "2017-06-20", winning_shows: 1 },
  references: [],
  moment: {
    heading: "T-ara's first win in over five years",
    body: "A sourced story.",
    citations: [
      { id: 4, reference_type: "article", provider: "soompi", external_id: "", url: "https://example.com/one", title: "Win report", publisher_name: "Soompi", is_official: false, published_at: null, last_verified_at: null },
      { id: 5, reference_type: "article", provider: "soompi", external_id: "", url: "https://example.com/two", title: "Later interview", publisher_name: "Soompi", is_official: false, published_at: null, last_verified_at: null },
    ],
  },
};

describe("WinMoments", () => {
  it("renders distinct citation labels and breakpoint-specific visible anchors", () => {
    render(<WinMoments wins={[win]} />);
    expect(screen.getByRole("link", { name: "Soompi — Win report" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Soompi — Later interview" })).toBeTruthy();
    const anchors = screen.getAllByRole("link", { name: "View this win" });
    expect(anchors.map((link) => link.getAttribute("href"))).toEqual(["#win-42", "#win-mobile-42"]);
  });

  it("shows two moments initially and toggles the remainder", () => {
    const wins = Array.from({ length: 5 }, (_, index) => ({
      ...win,
      id: 42 + index,
      date: `2017-06-${String(20 + index).padStart(2, "0")}`,
      moment: { ...win.moment!, heading: `Moment ${index + 1}` },
    }));
    render(<WinMoments wins={wins} />);

    expect(screen.getByRole("heading", { name: "Moment 1" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Moment 2" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Moment 3" })).toBeNull();

    const toggle = screen.getByRole("button", {
      name: "Show 3 more notable moments",
    });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(screen.getByRole("heading", { name: "Moment 5" })).toBeTruthy();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(toggle);
    expect(screen.queryByRole("heading", { name: "Moment 3" })).toBeNull();
  });
});
