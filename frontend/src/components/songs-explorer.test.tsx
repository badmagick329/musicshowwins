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
    const filters = options.queryKey[2] as { search: string; sort: string; page: number };
    return {
      data: { count: 101, next: filters.page === 1 ? "page-2" : null, previous: filters.page > 1 ? "page-1" : null, results: [{ id: 7, title: filters.search ? `${filters.search} Song` : "Archive Song", artist: { id: 3, name: "Artist" }, total_wins: 1, latest_win_date: "2025-01-01", winning_shows: 1 }] },
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
  it("debounces rapid typing into one normalized replacement update", () => {
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    render(<SongsExplorer />);
    const search = screen.getByLabelText("Search songs");
    fireEvent.change(search, { target: { value: "  new" } });
    fireEvent.change(search, { target: { value: "  new song  " } });

    act(() => vi.advanceTimersByTime(499));
    expect(replaceState).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenLastCalledWith(null, "", "/songs?search=new+song");
  });

  it("does not write history for an unchanged normalized search", () => {
    setUrl("/songs?search=love");
    vi.useFakeTimers();
    const replaceState = vi.spyOn(window.history, "replaceState");
    render(<SongsExplorer />);
    fireEvent.change(screen.getByLabelText("Search songs"), { target: { value: " love " } });

    act(() => vi.advanceTimersByTime(500));
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("pushes sort and pagination changes and resets the page for sorting", () => {
    setUrl("/songs?page=3");
    const pushState = vi.spyOn(window.history, "pushState");
    const view = render(<SongsExplorer />);
    fireEvent.change(screen.getByLabelText("Sort songs"), { target: { value: "artist" } });
    expect(pushState).toHaveBeenLastCalledWith(null, "", "/songs?sort=artist");

    view.rerender(<SongsExplorer />);
    setUrl("/songs");
    view.rerender(<SongsExplorer />);
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(pushState).toHaveBeenLastCalledWith(null, "", "/songs?page=2");
  });

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
