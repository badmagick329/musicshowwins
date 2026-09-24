import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import NotFound, { metadata } from "./not-found";

describe("global not found page", () => {
  it("uses a clear title and a route back home", () => {
    expect(metadata.title).toBe("Page Not Found");
    const html = renderToStaticMarkup(<NotFound />);
    expect(html).toContain("Page not found");
    expect(html).toContain("Return home");
    expect(html).toContain('href="/"');
  });
});
