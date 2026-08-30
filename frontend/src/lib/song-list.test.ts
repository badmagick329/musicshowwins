import { describe, expect, it } from "vitest";
import { defaultSongFilters, parseSongFilters, serializeSongFilters, songApiParams, updateSongFilters } from "./song-list";

describe("song discovery filters", () => {
  it("uses safe defaults and invalid URL fallbacks", () => {
    expect(parseSongFilters({})).toEqual(defaultSongFilters());
    expect(parseSongFilters({ sort: "newest", page: "0" })).toEqual(defaultSongFilters());
  });

  it("serializes shareable filters and API orderings", () => {
    expect(serializeSongFilters({ search: "  love ", sort: "artist", page: 2 }).toString()).toBe("search=love&sort=artist&page=2");
    expect(songApiParams({ search: "love", sort: "wins", page: 1 })).toEqual({ search: "love", ordering: "-total_wins,title,artist__name", page: 1 });
    expect(songApiParams({ search: "", sort: "title", page: 1 }).ordering).toBe("title,artist__name");
  });

  it("resets pagination for search and sort changes", () => {
    const filters = { search: "old", sort: "wins" as const, page: 3 };
    expect(updateSongFilters(filters, { search: "new" }).page).toBe(1);
    expect(updateSongFilters(filters, { sort: "artist" }).page).toBe(1);
    expect(updateSongFilters(filters, { page: 4 }).page).toBe(4);
  });
});
