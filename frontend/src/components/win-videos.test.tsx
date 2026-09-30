// @vitest-environment jsdom

import { cleanup, fireEvent, render, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { expectTypeOf } from "vitest";
import type { Win, WinReference } from "@/lib/api-shared";
import { ArtistWinHistory } from "./artist-win-history";
import { MobileWinVideoDisclosure, winVideoActionLabel, winVideoReferences } from "./win-videos";

const plausible = vi.fn();

beforeEach(() => {
  Object.assign(window, { plausible });
  plausible.mockClear();
});

afterEach(cleanup);

function reference(overrides: Partial<WinReference> = {}): WinReference {
  return { id: 1, reference_type: "video", provider: "youtube", external_id: "abc123", url: "https://www.youtube.com/watch?v=abc123", title: "Boom Boom Bass MV", publisher_name: "Mnet K-POP", is_official: true, artist_channel: false, published_at: null, last_verified_at: null, ...overrides };
}

function win(id: number, overrides: Partial<Win> = {}): Win {
  return { id, date: "2024-06-27", show: { id: 2, slug: "m-countdown", name: "M Countdown", active: true }, song: { id: 7, title: "Boom Boom Bass", artist: { id: 3, slug: "riize", name: "Riize" }, total_wins: 1, latest_win_date: "2024-06-27", winning_shows: 1 }, performed: null, references: [], milestones: { song_win: 2, song_show_win: 1, artist_win: 2 }, ...overrides };
}

const winName = "Boom Boom Bass by Riize, 27 Jun 2024, M Countdown";
const twoVideos = [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456", title: "Boom Boom Bass Encore" })];
const videoButton = (container: HTMLElement) => within(container).getByRole("button", { name: new RegExp(`videos? for ${winName}`) });

function viewport(width: number) {
  window.matchMedia = vi.fn((query: string) => ({ matches: width >= Number(/\d+/.exec(query)![0]) }) as MediaQueryList);
}

function expand(container: HTMLElement) {
  const button = videoButton(container);
  fireEvent.click(button);
  const panel = document.getElementById(button.getAttribute("aria-controls") ?? "");
  if (!panel) throw new Error("Expanded video panel did not render");
  return panel;
}

describe("win video references", () => {
  it("requires references on the Win type and exposes the action labels", () => {
    expectTypeOf<Win["references"]>().toEqualTypeOf<WinReference[]>();
    expect(winVideoReferences(win(1, { references: [reference()] }))).toHaveLength(1);
    expect(winVideoReferences(win(1, { references: [reference({ reference_type: "article" })] }))).toHaveLength(0);
    expect(winVideoActionLabel(1)).toBe("Watch on YouTube");
    expect(winVideoActionLabel(3)).toBe("3 videos");
  });

  it("offers one YouTube search only when no video exists", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference({ reference_type: "article" })] })]} />);
    const links = within(container).getAllByRole("link", { name: `Search YouTube for ${winName}` });
    expect(links).toHaveLength(1);
    const url = new URL(links[0].getAttribute("href")!);
    expect(url.origin + url.pathname).toBe("https://www.youtube.com/results");
    expect(url.searchParams.get("search_query")).toBe("Riize Boom Boom Bass 240627");
    expect(links[0].getAttribute("target")).toBe("_blank");
    expect(links[0].getAttribute("rel")).toBe("noopener noreferrer");
    expect(links[0].className).not.toContain("bg-brand-pink");
    expect(within(container).queryByRole("button", { name: /video/i })).toBeNull();
  });

  it("says the winner was absent instead of offering a search when no video exists", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { performed: false })]} />);
    expect(within(container).getAllByText("Absent from broadcast")).toHaveLength(1);
    expect(within(container).queryByRole("link", { name: /Search YouTube/ })).toBeNull();
  });

  it("still links a video for an absent winner when one exists", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { performed: false, references: [reference()] })]} />);
    expect(within(container).getByRole("link", { name: `Watch on YouTube for ${winName}` })).toBeTruthy();
    expect(within(container).queryByText("Absent from broadcast")).toBeNull();
  });

  it("renders one video as a single direct external Watch on YouTube link", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference()] })]} />);
    const links = within(container).getAllByRole("link", { name: `Watch on YouTube for ${winName}` });
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute("href")).toBe("https://www.youtube.com/watch?v=abc123");
    expect(links[0].getAttribute("target")).toBe("_blank");
    expect(links[0].getAttribute("rel")).toBe("noopener noreferrer");
    expect(links[0].textContent).toContain("Watch on YouTube");
    expect(within(container).queryByRole("link", { name: /Search YouTube/ })).toBeNull();
  });

  it("keeps the play and external-link icons and no chevron on the single-video action", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference()] })]} />);
    const link = within(container).getByRole("link", { name: `Watch on YouTube for ${winName}` });
    expect(link.querySelector("svg.lucide-play")).toBeTruthy();
    expect(link.querySelector("svg.lucide-external-link")).toBeTruthy();
    expect(link.querySelector("svg[class*='chevron']")).toBeNull();
    expect(link.className).toContain("whitespace-nowrap");
  });

  it("sizes both actions alike: large on phones, compact and right-aligned from md up", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference()] }), win(2, { references: [reference({ id: 5, title: "Second MV" }), reference({ id: 6, url: "https://www.youtube.com/watch?v=ghi789" })] })]} />);
    const link = within(container).getByRole("link", { name: `Watch on YouTube for ${winName}` });
    const button = within(container).getByRole("button", { name: `Choose from 2 videos for ${winName}` });
    for (const action of [link, button]) {
      const classes = action.className.split(" ");
      for (const name of ["min-h-10", "w-52", "md:h-8", "md:w-44", "md:ml-auto", "grid-cols-[0.875rem_1fr_0.875rem]"]) expect(classes).toContain(name);
      expect(action.childElementCount).toBe(3);
      expect(action.children[0].getAttribute("class")).toContain("size-3.5");
      expect(action.children[1].className).toContain("text-center");
      expect(action.children[2].getAttribute("class")).toContain("size-3.5");
    }
  });

  it("gives the single-video action no disclosure attributes and no panel", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference()] })]} />);
    viewport(1024);
    const link = within(container).getByRole("link", { name: `Watch on YouTube for ${winName}` });
    expect(link.getAttribute("aria-expanded")).toBeNull();
    expect(link.getAttribute("aria-controls")).toBeNull();
    fireEvent.click(link);
    expect(document.getElementById("win-videos-1")).toBeNull();
  });

  it("labels several videos with one outlined count button", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: twoVideos })]} />);
    const buttons = within(container).getAllByRole("button", { name: `Choose from 2 videos for ${winName}` });
    expect(buttons).toHaveLength(1);
    expect(buttons[0].textContent).toContain("2 videos");
    expect(buttons[0].className).toContain("whitespace-nowrap");
    expect(buttons[0].className).toContain("bg-card");
    expect(buttons[0].getAttribute("aria-expanded")).toBe("false");
    expect(buttons[0].getAttribute("aria-controls")).toBe("win-videos-1");
  });

  it("starts collapsed and expands and collapses on click, independent per win", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: twoVideos }), win(2, { references: [reference({ id: 5, title: "Second MV" }), reference({ id: 6, url: "https://www.youtube.com/watch?v=ghi789" })] })]} />);
    const buttons = within(container).getAllByRole("button", { name: /for Boom Boom Bass by Riize/ });
    expect(buttons).toHaveLength(2);
    const panel = (index: number) => document.getElementById(buttons[index].getAttribute("aria-controls") ?? "");

    fireEvent.click(buttons[0]);
    expect(panel(0)).toBeTruthy();
    expect(buttons[0].getAttribute("aria-expanded")).toBe("true");
    expect(panel(1)).toBeNull();

    fireEvent.click(buttons[1]);
    expect(panel(1)).toBeTruthy();
    expect(panel(0)).toBeTruthy();

    fireEvent.click(buttons[0]);
    expect(panel(0)).toBeNull();
    expect(panel(1)).toBeTruthy();
    expect(buttons[0].getAttribute("aria-expanded")).toBe("false");
  });

  it("spans the expanded list across the whole row on wide screens", () => {
    for (const hideSong of [false, true]) {
      const { container, unmount } = render(<ArtistWinHistory wins={[win(1, { references: twoVideos })]} hideSong={hideSong} />);
      const panel = expand(container);
      expect(panel.parentElement?.className).toContain("md:col-span-full");
      expect(panel.parentElement?.parentElement?.className).toContain("md:contents");
      unmount();
    }
  });

  it("renders titles, publisher names, and official status in the expanded list", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: twoVideos })]} />);
    const panel = expand(container);
    expect(within(panel).getByText("Boom Boom Bass MV")).toBeTruthy();
    expect(within(panel).getAllByText("Mnet K-POP")).toHaveLength(2);
    expect(within(panel).getAllByText("Official video")).toHaveLength(2);
  });

  it("labels fan uploads as a single link and in the expanded list", () => {
    const fan = reference({ id: 2, is_official: false, publisher_name: "Fan Channel", url: "https://www.youtube.com/watch?v=def456" });
    const single = render(<ArtistWinHistory wins={[win(1, { references: [fan] })]} />);
    const link = within(single.container).getByRole("link", { name: `Watch fan upload for ${winName}` });
    expect(link.textContent).toBe("Watch fan upload");
    expect(link.className).toContain("bg-action-pink");
    single.unmount();

    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference({ id: 1 }), fan] })]} />);
    const panel = expand(container);
    expect(within(panel).getAllByText("Official video")).toHaveLength(1);
    expect(within(panel).getAllByText("Fan upload")).toHaveLength(1);
  });

  it("labels uploads from the artist's own channel without calling them fan uploads", () => {
    const own = reference({ id: 2, is_official: false, artist_channel: true, publisher_name: "BLACKPINK", url: "https://www.youtube.com/watch?v=own" });
    const single = render(<ArtistWinHistory wins={[win(1, { references: [own] })]} />);
    const link = within(single.container).getByRole("link", { name: `Watch on YouTube for ${winName}` });
    fireEvent.click(link);
    expect(plausible).toHaveBeenLastCalledWith("Win video opened", expect.objectContaining({ props: expect.objectContaining({ source: "artist" }) }));
    single.unmount();

    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference({ id: 1 }), own] })]} />);
    const panel = expand(container);
    expect(within(panel).getAllByText("Artist channel")).toHaveLength(1);
    expect(within(panel).queryByText("Fan upload")).toBeNull();
  });

  it("tracks video opens with source and the placement the viewport had at click time", () => {
    const fan = reference({ id: 2, is_official: false, title: "Fan clip", url: "https://www.youtube.com/watch?v=def456" });
    const single = render(<ArtistWinHistory wins={[win(1, { references: [fan] })]} />);
    const link = within(single.container).getByRole("link", { name: `Watch fan upload for ${winName}` });
    viewport(375);
    fireEvent.click(link);
    expect(plausible).toHaveBeenLastCalledWith("Win video opened", { props: { show: "m-countdown", year: "2024", source: "fan", placement: "mobile" } });
    viewport(1280);
    fireEvent.click(link);
    expect(plausible).toHaveBeenLastCalledWith("Win video opened", { props: { show: "m-countdown", year: "2024", source: "fan", placement: "desktop" } });
    single.unmount();

    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference({ id: 1 }), fan] })]} />);
    const panel = expand(container);
    fireEvent.click(within(panel).getByRole("link", { name: /Boom Boom Bass MV/ }));
    expect(plausible).toHaveBeenLastCalledWith("Win video opened", { props: { show: "m-countdown", year: "2024", source: "official", placement: "list" } });
    expect(plausible).toHaveBeenCalledTimes(3);
  });

  it("tracks YouTube searches when no video exists", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1)]} />);
    viewport(1024);
    fireEvent.click(within(container).getByRole("link", { name: `Search YouTube for ${winName}` }));
    expect(plausible).toHaveBeenCalledWith("YouTube search clicked", { props: { show: "m-countdown", year: "2024", placement: "desktop" } });
  });

  it("links each listed video to the API URL in a new tab with the safe rel", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: twoVideos })]} />);
    const panel = expand(container);
    const link = within(panel).getByRole("link", { name: /Boom Boom Bass MV/ });
    expect(link.getAttribute("href")).toBe("https://www.youtube.com/watch?v=abc123");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("falls back to sensible labels for missing metadata", () => {
    const { container } = render(<ArtistWinHistory wins={[win(1, { references: [reference({ id: 1, title: "", publisher_name: "" }), reference({ id: 2, title: "", publisher_name: "", is_official: false, url: "https://www.youtube.com/watch?v=def456" })] })]} />);
    const panel = expand(container);
    expect(panel.textContent).toContain("Official video");
    expect(panel.textContent).toContain("Video");
    expect(panel.textContent).toContain("YouTube");
  });

  it("keeps an overlay list open while scrolling and closes it on an outside tap or Escape, returning focus on Escape", () => {
    const twoVideosWin = win(1, { references: twoVideos });
    const { container, getByRole, queryByRole } = render(<><MobileWinVideoDisclosure win={twoVideosWin} overlay /><p>outside</p></>);
    const button = getByRole("button", { name: `Choose from 2 videos for ${winName}` });
    fireEvent.click(button);
    expect(getByRole("list", { name: `Videos for ${winName}` }).closest(".absolute")).toBeTruthy();
    const outside = container.querySelector("p")!;
    fireEvent.pointerDown(outside);
    fireEvent.pointerCancel(outside);
    fireEvent.pointerUp(outside);
    expect(queryByRole("list")).toBeTruthy();
    fireEvent.pointerDown(outside);
    fireEvent.pointerUp(outside);
    expect(queryByRole("list")).toBeNull();
    fireEvent.click(button);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(queryByRole("list")).toBeNull();
    expect(document.activeElement).toBe(button);
  });
});
