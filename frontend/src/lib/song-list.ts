import { parsePositivePage } from "@/lib/api-shared";

export const songSorts = ["wins", "title", "artist"] as const;
export type SongSort = (typeof songSorts)[number];
export type SongFilters = { search: string; sort: SongSort; page: number };
export type SongSearchParams = Record<string, string | string[] | undefined>;

export const songSortLabels: Record<SongSort, string> = { wins: "Most wins", title: "Song A–Z", artist: "Artist A–Z" };
export const songOrderings: Record<SongSort, string> = {
  wins: "-total_wins,title,artist__name",
  title: "title,artist__name",
  artist: "artist__name,title",
};

export function defaultSongFilters(): SongFilters {
  return { search: "", sort: "wins", page: 1 };
}

export function normalizeSongFilters(filters: Partial<SongFilters>): SongFilters {
  return {
    search: typeof filters.search === "string" ? filters.search.trim() : "",
    sort: songSorts.includes(filters.sort as SongSort) ? filters.sort as SongSort : "wins",
    page: typeof filters.page === "number" && Number.isSafeInteger(filters.page) && filters.page > 0 ? filters.page : 1,
  };
}

export function parseSongFilters(params: SongSearchParams) {
  return normalizeSongFilters({
    search: typeof params.search === "string" ? params.search : undefined,
    sort: typeof params.sort === "string" ? params.sort as SongSort : undefined,
    page: parsePositivePage(params.page),
  });
}

export function songApiParams(filters: SongFilters) {
  return { search: filters.search || undefined, ordering: songOrderings[filters.sort], page: filters.page };
}

export function serializeSongFilters(filters: SongFilters) {
  const normalized = normalizeSongFilters(filters);
  const params = new URLSearchParams();
  if (normalized.search) params.set("search", normalized.search);
  if (normalized.sort !== "wins") params.set("sort", normalized.sort);
  if (normalized.page > 1) params.set("page", String(normalized.page));
  return params;
}

export function songsUrl(filters: SongFilters) {
  const search = serializeSongFilters(filters).toString();
  return search ? `/songs?${search}` : "/songs";
}

export function updateSongFilters(filters: SongFilters, update: Partial<SongFilters>) {
  const current = normalizeSongFilters(filters);
  const candidate = normalizeSongFilters({ ...current, ...update, page: update.page ?? current.page });
  const resetPage = candidate.search !== current.search || candidate.sort !== current.sort;
  return { ...candidate, page: resetPage ? 1 : candidate.page };
}
