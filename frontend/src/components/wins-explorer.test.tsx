// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WinsExplorer } from "./wins-explorer";

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
    const filters = options.queryKey[2] as { show: string; search: string };
    const title = filters.show === "the-show" ? "The Show Winner" : filters.show === "music-bank" ? "Music Bank Winner" : filters.search ? `${filters.search} Winner` : "Archive Winner";
    return {
      data: { count: 1, next: null, previous: null, results: [{ id: 1, date: "2025-01-01", show: { id: 1, slug: filters.show || "music-bank", name: filters.show === "the-show" ? "The Show" : "Music Bank", active: true }, song: { id: 7, title, artist: { id: 3, name: "Artist" }, total_wins: 1 } }] },
      isError: false,
      isFetching: false,
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
});

describe("WinsExplorer", () => {
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
    expect(screen.getByText("Archive Winner")).toBeTruthy();
  });

  it("debounces typing into one replacement history update", () => {
    setUrl("/wins");
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    render(<WinsExplorer />);
    const search = screen.getByLabelText("Search wins");
    fireEvent.change(search, { target: { value: "b" } });
    fireEvent.change(search, { target: { value: "bt" } });
    fireEvent.change(search, { target: { value: "bts" } });

    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenLastCalledWith(null, "", "/wins?search=bts");
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
    expect(screen.getByText("Music Bank Winner")).toBeTruthy();

    setUrl("/wins?show=the-show");
    window.dispatchEvent(new PopStateEvent("popstate"));
    view.rerender(<WinsExplorer />);
    expect((screen.getByLabelText("Music show") as HTMLSelectElement).value).toBe("the-show");
    expect(screen.getByText("The Show Winner")).toBeTruthy();
  });
});
