// @vitest-environment jsdom

import { cleanup, fireEvent, render, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { expectTypeOf } from "vitest";
import type { Win, WinReference } from "@/lib/api-shared";
import { RecentWins } from "./data-display";
import { ArtistWinHistory } from "./artist-win-history";
import { winVideoActionLabel, winVideoReferences } from "./win-videos";

afterEach(cleanup);

function reference(overrides: Partial<WinReference> = {}): WinReference {
  return { id: 1, reference_type: "video", provider: "youtube", external_id: "abc123", url: "https://www.youtube.com/watch?v=abc123", title: "Boom Boom Bass MV", publisher_name: "Mnet K-POP", is_official: true, published_at: null, last_verified_at: null, ...overrides };
}

function win(id: number, overrides: Partial<Win> = {}): Win {
  return { id, date: "2024-06-27", show: { id: 2, slug: "m-countdown", name: "M Countdown", active: true }, song: { id: 7, title: "Boom Boom Bass", artist: { id: 3, name: "Riize" }, total_wins: 1, latest_win_date: "2024-06-27", winning_shows: 1 }, references: [], ...overrides };
}

const winName = "Boom Boom Bass by Riize, 27 Jun 2024, M Countdown";
const desktop = (container: HTMLElement) => within(container.querySelector(".desktop-table") as HTMLElement);
const mobile = (container: HTMLElement) => within(container.querySelector(".mobile-record") as HTMLElement);
const videoButton = (container: HTMLElement) => desktop(container).getByRole("button", { name: new RegExp(`videos? for ${winName}`) });

function expandDesktop(container: HTMLElement) {
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
    expect(winVideoActionLabel(1)).toBe("Watch video");
    expect(winVideoActionLabel(3)).toBe("Choose video");
  });

  it("shows no video action when a win has no videos", () => {
    const { container } = render(<RecentWins wins={[win(1)]} />);
    expect(desktop(container).queryByRole("button", { name: /video/i })).toBeNull();
    expect(desktop(container).queryByRole("link", { name: /video/i })).toBeNull();
    expect(mobile(container).queryByRole("button", { name: /video/i })).toBeNull();
    expect(mobile(container).queryByRole("link", { name: /video/i })).toBeNull();
    expect(container.querySelector(".desktop-table")?.textContent).toContain("—");
    expect(container.querySelector(".mobile-record")?.textContent).not.toContain("—");
    expect(container.querySelector("td[colspan]")).toBeNull();
  });

  it("renders one video as a direct external Watch video link", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference()] })]} />);
    const link = desktop(container).getByRole("link", { name: `Watch video for ${winName}` });
    expect(link.getAttribute("href")).toBe("https://www.youtube.com/watch?v=abc123");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.textContent).toContain("Watch video");
    expect(mobile(container).getByRole("link", { name: `Watch video for ${winName}` })).toBeTruthy();
  });

  it("keeps the play and external-link icons and no chevron on the single-video action", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference()] })]} />);
    const link = desktop(container).getByRole("link", { name: `Watch video for ${winName}` });
    expect(link.querySelector("svg.lucide-play")).toBeTruthy();
    expect(link.querySelector("svg.lucide-external-link")).toBeTruthy();
    expect(link.querySelector("svg[class*='chevron']")).toBeNull();
    expect(link.className).toContain("whitespace-nowrap");
  });

  it("sizes both desktop actions identically with the same three-column layout", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference()] }), win(2, { references: [reference({ id: 5, title: "Second MV" }), reference({ id: 6, url: "https://www.youtube.com/watch?v=ghi789" })] })]} />);
    const link = desktop(container).getByRole("link", { name: `Watch video for ${winName}` });
    const button = desktop(container).getByRole("button", { name: `Choose from 2 videos for ${winName}` });
    expect(link.className).toBe(button.className);
    for (const className of [link.className, button.className]) {
      expect(className).toContain("h-8");
      expect(className).toContain("w-full");
      expect(className).toContain("grid-cols-[0.875rem_1fr_0.875rem]");
    }
    for (const action of [link, button]) {
      expect(action.childElementCount).toBe(3);
      expect(action.children[0].getAttribute("class")).toContain("size-3.5");
      expect(action.children[1].className).toContain("text-center");
      expect(action.children[2].getAttribute("class")).toContain("size-3.5");
    }
    const mobileLink = mobile(container).getByRole("link", { name: `Watch video for ${winName}` });
    const mobileButton = mobile(container).getByRole("button", { name: `Choose from 2 videos for ${winName}` });
    expect(mobileLink.className).toBe(mobileButton.className);
    expect(mobileLink.className).toContain("w-full");
    expect(mobileLink.className).toContain("min-h-11");
  });

  it("gives the single-video action no disclosure attributes and no panel", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference()] })]} />);
    const link = desktop(container).getByRole("link", { name: `Watch video for ${winName}` });
    expect(link.getAttribute("aria-expanded")).toBeNull();
    expect(link.getAttribute("aria-controls")).toBeNull();
    expect(document.getElementById("win-videos-desktop-1")).toBeNull();
    fireEvent.click(link);
    expect(document.getElementById("win-videos-desktop-1")).toBeNull();
    expect(container.querySelector("td[colspan]")).toBeNull();
  });

  it("labels several videos with a Choose video button whose name carries the count", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456" })] })]} />);
    const button = desktop(container).getByRole("button", { name: `Choose from 2 videos for ${winName}` });
    expect(button.textContent).toContain("Choose video");
    expect(button.className).toContain("whitespace-nowrap");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(button.getAttribute("aria-controls")).toBe("win-videos-desktop-1");
    expect(mobile(container).getByRole("button", { name: `Choose from 2 videos for ${winName}` }).getAttribute("aria-controls")).toBe("win-videos-mobile-1");
  });

  it("starts collapsed and expands and collapses on click, independent per win", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456" })] }), win(2, { references: [reference({ id: 5, title: "Second MV" }), reference({ id: 6, url: "https://www.youtube.com/watch?v=ghi789" })] })]} />);
    const buttons = desktop(container).getAllByRole("button", { name: /for Boom Boom Bass by Riize/ });
    expect(container.querySelector("td[colspan]")).toBeNull();

    fireEvent.click(buttons[0]);
    const firstPanel = document.getElementById(buttons[0].getAttribute("aria-controls") ?? "");
    expect(firstPanel).toBeTruthy();
    expect(buttons[0].getAttribute("aria-expanded")).toBe("true");
    expect(document.getElementById(buttons[1].getAttribute("aria-controls") ?? "")).toBeNull();

    fireEvent.click(buttons[1]);
    expect(document.getElementById(buttons[1].getAttribute("aria-controls") ?? "")).toBeTruthy();
    expect(document.getElementById(buttons[0].getAttribute("aria-controls") ?? "")).toBeTruthy();

    fireEvent.click(buttons[0]);
    expect(document.getElementById(buttons[0].getAttribute("aria-controls") ?? "")).toBeNull();
    expect(document.getElementById(buttons[1].getAttribute("aria-controls") ?? "")).toBeTruthy();
    expect(buttons[0].getAttribute("aria-expanded")).toBe("false");
  });

  it("renders titles, publisher names, and official status in the expanded list", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456", title: "Boom Boom Bass Encore" })] })]} />);
    const panel = expandDesktop(container);
    expect(within(panel).getByText("Boom Boom Bass MV")).toBeTruthy();
    expect(within(panel).getAllByText("Mnet K-POP")).toHaveLength(2);
    expect(within(panel).getAllByText("Official video")).toHaveLength(2);
  });

  it("links each listed video to the API URL in a new tab with the safe rel", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456", title: "Boom Boom Bass Encore" })] })]} />);
    const panel = expandDesktop(container);
    const link = within(panel).getByRole("link", { name: /Boom Boom Bass MV/ });
    expect(link.getAttribute("href")).toBe("https://www.youtube.com/watch?v=abc123");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("falls back to sensible labels for missing metadata", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1, title: "", publisher_name: "" }), reference({ id: 2, title: "", publisher_name: "", is_official: false, url: "https://www.youtube.com/watch?v=def456" })] })]} />);
    const panel = expandDesktop(container);
    expect(panel.textContent).toContain("Official video");
    expect(panel.textContent).toContain("Video");
    expect(panel.textContent).toContain("YouTube");
  });

  it("expands RecentWins desktop rows with colSpan 5 inside the table body", () => {
    const { container } = render(<RecentWins wins={[win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456" })] })]} />);
    const panel = expandDesktop(container);
    expect(container.querySelector('td[colspan="5"]')).toBeTruthy();
    expect(container.querySelector(".desktop-table tbody")?.contains(panel)).toBe(true);
  });

  it("expands ArtistWinHistory rows with colSpan 4, or 3 when the song column is hidden", () => {
    const wins = [win(1, { references: [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456" })] })];
    const withSong = render(<ArtistWinHistory wins={wins} />);
    expandDesktop(withSong.container);
    expect(withSong.container.querySelector('td[colspan="4"]')).toBeTruthy();
    withSong.unmount();

    const songOnly = render(<ArtistWinHistory wins={wins} hideSong emptyMessage="No wins with dates are recorded for this song." />);
    expandDesktop(songOnly.container);
    expect(songOnly.container.querySelector('td[colspan="3"]')).toBeTruthy();
    expect(mobile(songOnly.container).getByRole("button", { name: `Choose from 2 videos for ${winName}` })).toBeTruthy();
  });

  it("keeps video actions on one line with a matching Video column width in every win table", () => {
    const references = [reference({ id: 1 }), reference({ id: 2, url: "https://www.youtube.com/watch?v=def456" })];
    const views = [
      render(<RecentWins wins={[win(1, { references })]} />),
      render(<ArtistWinHistory wins={[win(1, { references })]} />),
      render(<ArtistWinHistory wins={[win(1, { references })]} hideSong />),
    ];
    const widths = views.map(({ container }) => {
      const header = desktop(container).getByRole("columnheader", { name: "Video" });
      const cell = videoButton(container).closest("td");
      expect(header.className).toContain("w-44");
      expect(cell?.className).toContain("w-44");
      return `${header.className} ${cell?.className}`;
    });
    expect(new Set(widths.map((value) => value.match(/w-\d+/)?.[0])).size).toBe(1);
    views.forEach(({ unmount }) => unmount());
  });
});
