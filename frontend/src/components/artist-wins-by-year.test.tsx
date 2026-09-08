// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Artist, Win } from "@/lib/api-shared";
import { artistYears, datedArtistWins, parseArtistYear } from "@/lib/artist-years";
import { ArtistWinsByYear } from "./artist-wins-by-year";

const artist: Artist = { id: 3, name: "Artist & Collaborator", total_wins: 4, winning_songs: 2, latest_win_date: "2024-01-01" };
function win(id: number, year: number, song = 1, show = 1): Win {
  return { id, date: `${year}-01-01`, song: { id: song, title: `Song ${song}`, artist, total_wins: 99, winning_shows: 9, latest_win_date: null }, show: { id: show, name: `Show ${show}`, slug: "music-bank", active: true }, references: [], moment: { heading: `Moment ${id}`, body: `Story ${id}`, citations: [] } };
}
const wins = [win(4, 2024, 2, 2), win(3, 2024), win(2, 2024), win(1, 2022)];
const plausible = vi.fn();
beforeEach(() => {
  window.history.replaceState(null, "", "/artists/3");
  Object.assign(window, { plausible });
  plausible.mockClear();
});
afterEach(cleanup);

describe("artist year exploration", () => {
  it("includes gaps and excludes undated aggregates", () => {
    const records = [...wins, { ...wins[0], date: "" }];
    expect(artistYears(records)).toEqual([{ year: "2022", count: 1 }, { year: "2023", count: 0 }, { year: "2024", count: 3 }]);
    expect(datedArtistWins(records)).toHaveLength(4);
    for (const value of [undefined, "bad", "2024x", ["2024", "2023"]]) expect(parseArtistYear(value)).toBeNull();
  });

  it("agrees across chart, totals, songs, shows, history and moments", () => {
    render(<ArtistWinsByYear artist={artist} wins={wins} initialYear={null} />);
    expect(plausible).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "2024: 3 recorded wins" }));
    expect(window.location.search).toBe("?year=2024");
    expect(screen.getByRole("heading", { name: "Wins in 2024" }).parentElement!.textContent).toContain("3 recorded wins · 2 winning songs");
    const songs = screen.getByRole("region", { name: "Songs" });
    expect(within(songs).getAllByRole("row").map((row) => row.textContent)).toEqual(["RankSongWins", "1Song 12", "2Song 21"]);
    const shows = screen.getByRole("region", { name: "Wins by show" });
    expect(within(shows).getAllByRole("row").map((row) => row.textContent)).toEqual(["ShowWins", "Show 12", "Show 21"]);
    expect(within(screen.getByRole("region", { name: "Win history" })).getAllByRole("row")).toHaveLength(4);
    expect(screen.queryByText("Moment 1")).toBeNull();
    expect(screen.getByRole("button", { name: "2024: 3 recorded wins" }).getAttribute("aria-pressed")).toBe("true");
    expect(plausible).toHaveBeenCalledWith("Artist year selected", { props: { artist: artist.name, artist_id: "3", year: "2024", source: "chart" } });
    fireEvent.click(within(songs).getAllByRole("link", { name: "Song 1" })[0]);
    expect(plausible).toHaveBeenLastCalledWith("Artist year song opened", { props: { artist: artist.name, artist_id: "3", year: "2024", song_id: "1" } });
  });

  it("supports empty years and an explicit return to all years", () => {
    render(<ArtistWinsByYear artist={artist} wins={wins} initialYear={null} />);
    fireEvent.change(screen.getByLabelText("Year"), { target: { value: "2023" } });
    expect(screen.getByText("No wins are recorded for 2023.")).toBeTruthy();
    for (const name of ["Songs", "Wins by show", "Win history", "Notable moments"]) expect(screen.queryByRole("region", { name })).toBeNull();
    expect(screen.getByRole("list", { name: "Recorded wins per year" }).children).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Reset to all years" }));
    expect(window.location.search).toBe("");
    expect(screen.getByRole("heading", { name: "Wins across all years" }).parentElement!.textContent).toContain("4 recorded wins · 2 winning songs");
    expect(plausible).toHaveBeenLastCalledWith("Artist year selected", { props: { artist: artist.name, artist_id: "3", year: "all", source: "all-years" } });
  });

  it("restores shared links, Back and Forward without counting rendering as use", async () => {
    window.history.replaceState(null, "", "/artists/3?year=2022");
    render(<ArtistWinsByYear artist={artist} wins={wins} initialYear="2022" />);
    expect(screen.getByRole("heading", { name: "Wins in 2022" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Year"), { target: { value: "2024" } });
    await act(async () => { window.history.back(); await new Promise((resolve) => window.addEventListener("popstate", resolve, { once: true })); });
    expect((screen.getByLabelText("Year") as HTMLSelectElement).value).toBe("2022");
    await act(async () => { window.history.forward(); await new Promise((resolve) => window.addEventListener("popstate", resolve, { once: true })); });
    expect((screen.getByLabelText("Year") as HTMLSelectElement).value).toBe("2024");
    expect(plausible).toHaveBeenCalledTimes(1);
  });

  it("uses singular wording and shows only relevant controls and scope notes", () => {
    const view = render(<ArtistWinsByYear artist={artist} wins={[wins[0]]} initialYear={null} />);
    expect(screen.getByRole("heading", { name: "Wins across all years" }).parentElement!.textContent).toContain("1 recorded win · 1 winning song");
    expect(screen.queryByRole("button", { name: "Copy link" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset to all years" })).toBeNull();
    expect(screen.queryByText("Undated history is excluded.")).toBeNull();
    view.rerender(<ArtistWinsByYear artist={artist} wins={[wins[0], { ...wins[1], date: "" }]} initialYear={null} />);
    expect(screen.getByText("Undated history is excluded.")).toBeTruthy();
  });

  it("keeps one-year and no-date histories useful", () => {
    const view = render(<ArtistWinsByYear artist={artist} wins={[wins[0]]} initialYear={null} />);
    expect(screen.getByRole("list", { name: "Recorded wins per year" }).children).toHaveLength(1);
    view.rerender(<ArtistWinsByYear artist={artist} wins={[]} initialYear={null} />);
    expect(screen.queryByRole("list", { name: "Recorded wins per year" })).toBeNull();
    expect(screen.getByText(/A yearly chart is not available/)).toBeTruthy();
  });
});
