// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WinsExplorer } from "./wins-explorer";

const queryState = vi.hoisted(() => ({ isFetching: false, isPlaceholderData: false, videoReferences: [] as unknown[] }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("@tanstack/react-query", () => ({
  keepPreviousData: () => undefined,
  queryOptions: <T,>(options: T) => options,
  useQuery: (options: { queryKey: readonly unknown[] }) => {
    if (options.queryKey[0] === "shows") {
      return {
        data: { count: 2, next: null, previous: null, results: [
          { id: 1, slug: "music-bank", name: "Music Bank", active: true },
          { id: 2, slug: "the-show", name: "The Show", active: true },
        ] },
        isError: false,
        isFetching: false,
      };
    }
    const filters = options.queryKey[2] as { show: string; search: string; page: number };
    const title = filters.show === "the-show" ? "The Show Winner" : filters.show === "music-bank" ? "Music Bank Winner" : filters.search ? `${filters.search} Winner` : "Archive Winner";
    return {
      data: { count: 201, next: filters.page < 3 ? "next" : null, previous: filters.page > 1 ? "previous" : null, results: [
        { id: 1, date: "2025-01-01", show: { id: 1, slug: filters.show || "music-bank", name: filters.show === "the-show" ? "The Show" : "Music Bank", active: true }, song: { id: 7, title, artist: { id: 3, name: "Artist" }, total_wins: 1 }, references: queryState.videoReferences },
        { id: 2, date: "2025-01-02", show: { id: 3, slug: "show-champion", name: "Show Champion", active: true }, song: { id: 8, title: "Second Winner", artist: { id: 4, name: "Another Artist" }, total_wins: 1 }, references: [] },
      ] },
      isError: false,
      isFetching: queryState.isFetching,
      isPlaceholderData: queryState.isPlaceholderData,
      isLoading: false,
      refetch: vi.fn(),
    };
  },
}));

function setUrl(path: string) {
  window.history.replaceState(null, "", path);
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  setUrl("/wins");
  queryState.isFetching = false;
  queryState.isPlaceholderData = false;
  queryState.videoReferences = [];
});

describe("WinsExplorer", () => {
  it("uses a semantic desktop table and retains stacked mobile records", () => {
    const { container } = render(<WinsExplorer />);
    expect(screen.getByRole("table", { name: "Filtered music show wins" })).toBeTruthy();
    for (const heading of ["Date", "Artist", "Song", "Music show", "Video"]) expect(screen.getByRole("columnheader", { name: heading })).toBeTruthy();
    expect(container.querySelectorAll("article")).toHaveLength(2);
    expect(container.innerHTML).not.toContain("winsGridColumns");
  });

  it("expands video references beneath the same win in the desktop table and mobile records", () => {
    queryState.videoReferences = [{ id: 5, reference_type: "video", provider: "youtube", external_id: "x1", url: "https://www.youtube.com/watch?v=x1", title: "Archive Winner MV", publisher_name: "KBS World", is_official: true, published_at: null, last_verified_at: null }];
    const { container } = render(<WinsExplorer />);
    const desktopScope = within(container.querySelector(".desktop-table") as HTMLElement);
    const button = desktopScope.getByRole("button", { name: "Watch video for Archive Winner by Artist, 01 Jan 2025, Music Bank" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    const panel = document.getElementById(button.getAttribute("aria-controls") ?? "");
    expect(panel).toBeTruthy();
    expect(container.querySelector('td[colspan="5"]')).toBeTruthy();
    expect(container.querySelector(".desktop-table tbody")?.contains(panel)).toBe(true);
    const link = within(panel as HTMLElement).getByRole("link", { name: /Archive Winner MV/ });
    expect(link.getAttribute("href")).toBe("https://www.youtube.com/watch?v=x1");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");

    const mobileButton = within(container.querySelector(".mobile-record") as HTMLElement).getByRole("button", { name: "Watch video for Archive Winner by Artist, 01 Jan 2025, Music Bank" });
    fireEvent.click(mobileButton);
    expect(document.getElementById(mobileButton.getAttribute("aria-controls") ?? "")?.textContent).toContain("KBS World");
  });

  it("shows total pages and waits for real requested-page data before scrolling", () => {
    Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
    queryState.isFetching = true;
    queryState.isPlaceholderData = true;
    const view = render(<WinsExplorer />);
    expect(screen.getByText("Page 1 of 3")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    view.rerender(<WinsExplorer />);
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();

    queryState.isFetching = false;
    queryState.isPlaceholderData = false;
    view.rerender(<WinsExplorer />);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(1);
  });

  it("does not scroll for background refetches or filter changes", () => {
    Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
    const view = render(<WinsExplorer />);
    queryState.isFetching = true;
    view.rerender(<WinsExplorer />);
    queryState.isFetching = false;
    view.rerender(<WinsExplorer />);
    fireEvent.change(screen.getByLabelText("Music show"), { target: { value: "the-show" } });
    view.rerender(<WinsExplorer />);
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it("links song titles to their detail pages", () => {
    render(<WinsExplorer />);
    expect(screen.getAllByRole("link", { name: "Archive Winner" }).every((link) => link.getAttribute("href") === "/songs/7")).toBe(true);
    expect(screen.getAllByRole("link", { name: "Filter wins by Music Bank" }).every((link) => link.getAttribute("href") === "/wins?show=music-bank#wins-results-title")).toBe(true);
  });

  it("clears filters from an initially filtered URL", () => {
    setUrl("/wins?show=music-bank&year=2025");
    const pushState = vi.spyOn(window.history, "pushState");
    const view = render(<WinsExplorer />);

    expect((screen.getByLabelText("Music show") as HTMLSelectElement).value).toBe("music-bank");
    expect((screen.getByLabelText("Year") as HTMLSelectElement).value).toBe("2025");
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(pushState).toHaveBeenLastCalledWith(null, "", "/wins");

    view.rerender(<WinsExplorer />);
    expect((screen.getByLabelText("Music show") as HTMLSelectElement).value).toBe("");
    expect((screen.getByLabelText("Year") as HTMLSelectElement).value).toBe("");
    expect(screen.getAllByText("Archive Winner")).toHaveLength(2);
  });

  it("debounces typing into one replacement history update", () => {
    setUrl("/wins");
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    const view = render(<WinsExplorer />);
    const search = screen.getByLabelText("Search wins");
    search.focus();
    fireEvent.change(search, { target: { value: "b" } });
    fireEvent.change(search, { target: { value: "bt" } });
    fireEvent.change(search, { target: { value: "bts" } });

    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenLastCalledWith(null, "", "/wins?search=bts");
    view.rerender(<WinsExplorer />);
    expect(document.activeElement).toBe(search);
  });

  it("does not write history for an unchanged normalized search", () => {
    setUrl("/wins?search=bts");
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    render(<WinsExplorer />);
    fireEvent.change(screen.getByLabelText("Search wins"), { target: { value: " bts " } });

    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("derives controls and results from Back or Forward URL changes", () => {
    setUrl("/wins?show=music-bank");
    const view = render(<WinsExplorer />);
    expect((screen.getByLabelText("Music show") as HTMLSelectElement).value).toBe("music-bank");
    expect(screen.getAllByText("Music Bank Winner")).toHaveLength(2);

    setUrl("/wins?show=the-show");
    window.dispatchEvent(new PopStateEvent("popstate"));
    view.rerender(<WinsExplorer />);
    expect((screen.getByLabelText("Music show") as HTMLSelectElement).value).toBe("the-show");
    expect(screen.getAllByText("The Show Winner")).toHaveLength(2);
  });
});
