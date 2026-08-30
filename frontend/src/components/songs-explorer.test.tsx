// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SongsExplorer } from "./songs-explorer";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("@tanstack/react-query", () => ({
  keepPreviousData: () => undefined,
  queryOptions: <T,>(options: T) => options,
  useQuery: (options: { queryKey: readonly unknown[] }) => {
    const filters = options.queryKey[2] as { search: string; sort: string };
    return {
      data: { count: 1, next: null, previous: null, results: [{ id: 7, title: filters.search ? `${filters.search} Song` : "Archive Song", artist: { id: 3, name: "Artist" }, total_wins: 1, latest_win_date: "2025-01-01", winning_shows: 1 }] },
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
  setUrl("/songs");
});

describe("SongsExplorer search", () => {
  it("retains focus and supports continued typing after a debounced URL update", () => {
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    const view = render(<SongsExplorer />);
    const search = screen.getByLabelText("Search songs") as HTMLInputElement;
    search.focus();
    fireEvent.change(search, { target: { value: "d" } });
    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).toHaveBeenLastCalledWith(null, "", "/songs?search=d");

    view.rerender(<SongsExplorer />);
    expect(document.activeElement).toBe(search);
    fireEvent.change(search, { target: { value: "dy" } });
    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).toHaveBeenCalledTimes(2);
    expect(replaceState).toHaveBeenLastCalledWith(null, "", "/songs?search=dy");
  });

  it("syncs the visible input with Back and Forward URL search changes", () => {
    const view = render(<SongsExplorer />);
    const search = screen.getByLabelText("Search songs") as HTMLInputElement;
    setUrl("/songs?search=love");
    window.dispatchEvent(new PopStateEvent("popstate"));
    view.rerender(<SongsExplorer />);
    expect(search.value).toBe("love");

    setUrl("/songs?search=dynamite");
    window.dispatchEvent(new PopStateEvent("popstate"));
    view.rerender(<SongsExplorer />);
    expect(search.value).toBe("dynamite");
  });
});
