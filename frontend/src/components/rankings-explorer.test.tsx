// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RankingsExplorer } from "./rankings-explorer";
import { parseRankingSelection } from "@/lib/rankings";

const queryState = vi.hoisted(() => ({ pending: false, previousUrl: "/rankings" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));
vi.mock("@tanstack/react-query", () => ({
  queryOptions: <T,>(options: T) => options,
  keepPreviousData: <T,>(data: T) => data,
  useQuery: () => {
    if (!queryState.pending) queryState.previousUrl = window.location.href;
    const selection = parseRankingSelection(Object.fromEntries(new URL(queryState.previousUrl, window.location.href).searchParams), "2026-09-14");
    const kind = selection.kind;
    const page = selection.page;
    const row = kind === "artists"
      ? { rank: page === 2 ? 2 : 1, wins: 3, artist: { id: 7, name: "Alpha" } }
      : { rank: page === 2 ? 2 : 1, wins: 3, song: { id: 9, title: "First", artist: { id: 7, name: "Alpha" } } };
    return { data: { count: 101, previous: page > 1 ? "previous" : null, next: page === 1 ? "next" : null, results: [row], selection }, isLoading: false, isError: false, isFetching: queryState.pending, isPlaceholderData: queryState.pending, refetch: vi.fn() };
  },
}));

beforeEach(() => { Element.prototype.scrollIntoView = vi.fn(); });
afterEach(() => { cleanup(); queryState.pending = false; queryState.previousUrl = "/rankings"; window.history.replaceState(null, "", "/rankings"); });

describe("RankingsExplorer", () => {
  it("preserves a previous year while switching kind and paging, and links to exact wins", () => {
    window.history.replaceState(null, "", "/rankings?year=2025");
    const view = render(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getByRole("button", { name: "Songs" }).className).toContain("bg-action-pink text-white");
    expect(screen.getByRole("heading", { name: "Top songs of 2025" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Artists" }));
    expect(window.location.search).toBe("?kind=artists&year=2025");
    view.rerender(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getByRole("button", { name: "Artists" }).className).toContain("bg-action-pink text-white");
    expect(screen.getByRole("heading", { name: "Top artists of 2025" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /View 3 wins for Alpha/ })[0].getAttribute("href")).toBe("/wins?artist=7&date_from=2025-01-01&date_to=2025-12-31#wins-results-title");
    fireEvent.click(screen.getByRole("link", { name: "Next" }));
    expect(window.location.search).toBe("?kind=artists&year=2025&page=2");
    view.rerender(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
  });

  it("applies inclusive custom dates and reports reversed ranges", () => {
    const view = render(<RankingsExplorer today="2026-09-14" />);
    fireEvent.change(screen.getByRole("combobox", { name: "Period" }), { target: { value: "custom" } });
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2025-02-02" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2025-02-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(screen.getByRole("alert").textContent).toMatch(/Start date/);
    expect(window.location.pathname + window.location.search).toBe("/rankings");
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2025-02-02" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(window.location.search).toBe("?period=custom&date_from=2025-02-02&date_to=2025-02-02");
    view.rerender(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getByRole("heading", { name: "Top songs from 2025-02-02 to 2025-02-02" })).toBeTruthy();
  });

  it("keeps the previous ranking rows and their links visible while another ranking loads", () => {
    const view = render(<RankingsExplorer today="2026-09-14" />);
    queryState.pending = true;
    fireEvent.click(screen.getByRole("button", { name: "Artists" }));
    view.rerender(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getByRole("status").textContent).toBe("Updating results…");
    expect(screen.queryByText("Loading rankings…")).toBeNull();
    expect(screen.getByRole("heading", { name: "Top songs of 2026" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /View 3 wins for First/ })[0].getAttribute("href")).toBe("/wins?song=9&date_from=2026-01-01&date_to=2026-09-14#wins-results-title");
    queryState.pending = false;
    view.rerender(<RankingsExplorer today="2026-09-14" />);
    expect(screen.getByRole("heading", { name: "Top artists of 2026" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /View 3 wins for Alpha/ })[0]).toBeTruthy();
  });
});
