// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TopWinsThisYearLink } from "./top-wins-this-year-link";

const plausible = vi.fn();

beforeEach(() => {
  Object.assign(window, { plausible });
  plausible.mockClear();
});
afterEach(cleanup);

describe("TopWinsThisYearLink", () => {
  it("emits the event once for each activation without changing link behavior", () => {
    render(<TopWinsThisYearLink />);
    const link = screen.getByRole("link", { name: "Top wins this year →" });

    expect(link.getAttribute("href")).toBe("/rankings");
    expect(fireEvent.click(link)).toBe(true);
    expect(fireEvent.click(link, { ctrlKey: true })).toBe(true);
    expect(plausible).toHaveBeenCalledTimes(2);
    expect(plausible).toHaveBeenNthCalledWith(1, "Top wins this year clicked", { props: {} });
    expect(plausible).toHaveBeenNthCalledWith(2, "Top wins this year clicked", { props: {} });
  });
});
