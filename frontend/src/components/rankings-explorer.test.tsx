// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RankingsExplorer } from "./rankings-explorer";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  useRouter: () => ({ push: (url: string) => window.history.pushState(null, "", url) }),
}));
vi.mock("@tanstack/react-query", () => ({
  queryOptions: <T,>(options: T) => options,
  useQuery: (options: { queryKey: [string, string, Record<string, string | number>] }) => {
    const kind = options.queryKey[1];
    const page = Number(options.queryKey[2].page);
    const row = kind === "artists"
      ? { rank: page === 2 ? 2 : 1, wins: 3, artist: { id: 7, name: "Alpha" } }
      : { rank: page === 2 ? 2 : 1, wins: 3, song: { id: 9, title: "First", artist: { id: 7, name: "Alpha" } } };
    return { data: { count: 101, previous: page > 1 ? "previous" : null, next: page === 1 ? "next" : null, results: [row] }, isLoading: false, isError: false, refetch: vi.fn() };
  },
}));

afterEach(() => { cleanup(); window.history.replaceState(null, "", "/rankings"); });

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
});
