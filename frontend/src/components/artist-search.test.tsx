// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ArtistSearch } from "./artist-search";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("ArtistSearch", () => {
  it("keeps search instructions out of search-result snippets", () => {
    render(<ArtistSearch query="bts" results={[]} resultCount={0} />);

    const instructions = screen.getByText("Find an artist").closest("div[data-nosnippet]");
    expect(instructions).not.toBeNull();
    expect(instructions?.tagName).toBe("DIV");
    expect(instructions?.contains(screen.getByText("Search by artist name or known alias."))).toBe(true);
    expect(instructions?.contains(screen.getByRole("textbox", { name: "Artist name or alias" }))).toBe(false);
    expect(instructions?.contains(screen.getByText('Results for "bts"'))).toBe(false);
  });

  it("keeps the focused input when results update", () => {
    vi.useFakeTimers();
    const view = render(<ArtistSearch query="" results={[]} resultCount={0} />);
    const input = screen.getByRole("textbox", { name: "Artist name or alias" });
    input.focus();

    view.rerender(<ArtistSearch query="bts" results={[]} resultCount={0} />);

    expect(screen.getByRole("textbox", { name: "Artist name or alias" })).toBe(input);
    expect(document.activeElement).toBe(input);
    expect(input).toHaveProperty("value", "bts");
  });
});
