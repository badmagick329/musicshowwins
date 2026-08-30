import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Pagination } from "./pagination";

describe("artist pagination", () => {
  it("shows total pages and targets the results anchor", () => {
    const html = renderToStaticMarkup(<Pagination page={2} totalCount={201} hasPrevious hasNext search="ive" sort="wins" />);
    expect(html).toContain("Page 2 of 3");
    expect(html).toContain('href="/artists?sort=wins&amp;search=ive#artist-results-title"');
    expect(html).toContain('href="/artists?sort=wins&amp;search=ive&amp;page=3#artist-results-title"');
  });
});
