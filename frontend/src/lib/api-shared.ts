export type ApiPage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type ApiParams = Record<string, string | number | undefined>;

export type Artist = {
  id: number;
  name: string;
  total_wins: number;
  winning_songs: number;
  latest_win_date: string | null;
};
export type Song = { id: number; title: string; artist: Pick<Artist, "id" | "name">; total_wins: number; latest_win_date: string | null; winning_shows: number };
export type ShowSummary = { id: number; slug: string; name: string; active: boolean };
export type Show = ShowSummary & {
  id: number;
  slug: string;
  name: string;
  active: boolean;
  total_wins: number;
  first_win_date: string | null;
  latest_win_date: string | null;
  latest_win: {
    id: number;
    date: string;
    song: Pick<Song, "id" | "title"> & { artist: Pick<Artist, "id" | "name"> };
  } | null;
};
export type CorrectionReport = {
  page_or_record: string;
  correction: string;
  supporting_source: string;
  contact: string;
  website: string;
};
export type Win = { id: number; date: string; show: ShowSummary; song: Song };
export type ArtistLeaderboardRow = { rank: number; wins: number; artist: Pick<Artist, "id" | "name"> };
export type SongLeaderboardRow = { rank: number; wins: number; song: Pick<Song, "id" | "title" | "artist"> };
export type HomeData = {
  artists: ArtistLeaderboardRow[];
  songs: SongLeaderboardRow[];
  wins: Win[];
  shows: Show[];
  artistResults: Artist[];
  artistResultCount: number;
  errors: string[];
};

export class ApiRequestError extends Error {
  constructor(public status: number, message = `API request failed (${status}).`) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export function serializeApiParams(params: ApiParams = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  return search;
}

export function buildApiUrl(baseUrl: string, path: string, params: ApiParams = {}) {
  const url = new URL(`${baseUrl.replace(/\/$/, "")}${path}`);
  url.search = serializeApiParams(params).toString();
  return url.toString();
}

export function parseApiPage<T>(value: unknown): ApiPage<T> {
  if (!value || typeof value !== "object") throw new Error("API returned an invalid page.");
  const page = value as Record<string, unknown>;
  const validLink = (link: unknown) => link === null || typeof link === "string";
  if (!Array.isArray(page.results) || typeof page.count !== "number" || !Number.isInteger(page.count) || page.count < 0 || !validLink(page.next) || !validLink(page.previous)) {
    throw new Error("API returned an invalid page.");
  }
  return page as ApiPage<T>;
}

export async function requestJson<T>(url: string, signal?: AbortSignal) {
  const response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok) throw new ApiRequestError(response.status);
  return (await response.json()) as T;
}

export type ApiTransport = {
  requestPage<T>(path: string, params?: ApiParams, signal?: AbortSignal): Promise<ApiPage<T>>;
};

export function parsePositivePage(value: string | string[] | undefined) {
  if (typeof value !== "string" || !/^\d+$/.test(value)) return 1;
  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}
