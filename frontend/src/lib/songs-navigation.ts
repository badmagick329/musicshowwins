import { defaultSongFilters, parseSongFilters, songsUrl, updateSongFilters, type SongFilters } from "@/lib/song-list";

export type SongHistoryMode = "push" | "replace";

export function songFiltersFromSearchParams(searchParams: URLSearchParams) {
  const params: Record<string, string> = {};
  searchParams.forEach((value, key) => { params[key] = value; });
  return parseSongFilters(params);
}

export function writeSongHistory(current: SongFilters, update: Partial<SongFilters>, mode: SongHistoryMode = "push") {
  const filters = updateSongFilters(current, update);
  const url = songsUrl(filters);
  if (url === songsUrl(current)) return false;
  window.history[`${mode}State`](null, "", url);
  return true;
}

export function clearSongHistory(current: SongFilters) {
  return writeSongHistory(current, defaultSongFilters());
}
