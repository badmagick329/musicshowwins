// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ArchivePageLink } from "./archive-page-link";

afterEach(cleanup);

it("exposes a crawlable URL while handling ordinary clicks in place", () => {
  const navigate = vi.fn();
  render(<ArchivePageLink href="/songs?page=2" onNavigate={navigate}>Next</ArchivePageLink>);
  const link = screen.getByRole("link", { name: "Next" });
  expect(link.getAttribute("href")).toBe("/songs?page=2");
  expect(fireEvent.click(link)).toBe(false);
  expect(navigate).toHaveBeenCalledOnce();
});

it("leaves modified clicks to the browser", () => {
  const navigate = vi.fn();
  render(<ArchivePageLink href="/songs?page=2" onNavigate={navigate}>Next</ArchivePageLink>);
  expect(fireEvent.click(screen.getByRole("link"), { ctrlKey: true })).toBe(true);
  expect(navigate).not.toHaveBeenCalled();
});
