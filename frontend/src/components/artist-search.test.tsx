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
