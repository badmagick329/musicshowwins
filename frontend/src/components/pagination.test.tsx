import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ArchiveResultsSummary, Pagination } from "./pagination";

describe("artist pagination", () => {
  it("shows total pages and targets the results anchor", () => {
    const html = renderToStaticMarkup(<Pagination page={2} totalCount={201} hasPrevious hasNext search="ive" sort="wins" />);
    expect(html).toContain("Page 2 of 3");
    expect(html).toContain('href="/artists?sort=wins&amp;search=ive#artist-results-title"');
    expect(html).toContain('href="/artists?sort=wins&amp;search=ive&amp;page=3#artist-results-title"');
  });
});

describe("ArchiveResultsSummary", () => {
  it("shows the current range, total, and page near the results heading", () => {
    const html = renderToStaticMarkup(<ArchiveResultsSummary totalCount={984} page={2} resultCount={100} singular="song" plural="songs" />);
    expect(html).toContain("101–200 of 984 songs · Page 2 of 10");
    expect(html).toContain('aria-live="polite"');
  });
});
