export type ApiPage<T> = { count: number; next: string | null; previous: string | null; results: T[] };
import { artistOrderings, type ArtistSort } from "@/lib/artist-list";

export type Artist = { id: number; name: string; total_wins: number; winning_songs: number; latest_win_date: string | null };
export type Song = { id: number; title: string; artist: Pick<Artist, "id" | "name">; total_wins: number };
export type Show = { id: number; slug: string; name: string; active: boolean };
export type Win = { id: number; date: string; show: Show; song: Song };
export type ArtistLeaderboardRow = { rank: number; wins: number; artist: Pick<Artist, "id" | "name"> };
export type SongLeaderboardRow = { rank: number; wins: number; song: Omit<Song, "total_wins"> };
export type HomeData = { artists: ArtistLeaderboardRow[]; songs: SongLeaderboardRow[]; wins: Win[]; shows: Show[]; artistResults: Artist[]; artistResultCount: number; errors: string[] };

const defaultBaseUrl = "http://127.0.0.1:8000/api/v1";

export class ApiRequestError extends Error {
  constructor(public status: number, message = `API request failed (${status}).`) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export function getApiBaseUrl() {
  return (process.env.DJANGO_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultBaseUrl).replace(/\/$/, "");
}

export function buildApiUrl(path: string, params: Record<string, string | number | undefined> = {}) {
  const url = new URL(`${getApiBaseUrl()}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }
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

async function requestJson<T>(path: string, params?: Record<string, string | number | undefined>) {
  const response = await fetch(buildApiUrl(path, params), { cache: "no-store" });
  if (!response.ok) throw new ApiRequestError(response.status);
  return (await response.json()) as T;
}

export async function requestPage<T>(path: string, params?: Record<string, string | number | undefined>) {
  return parseApiPage<T>(await requestJson<unknown>(path, params));
}

export function parsePositivePage(value: string | string[] | undefined) {
  if (typeof value !== "string" || !/^\d+$/.test(value)) return 1;
  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

function nextPageNumber(next: string, expectedPath: string) {
  let url: URL;
  try { url = new URL(next, getApiBaseUrl()); } catch { throw new Error("API returned malformed pagination."); }
  const basePath = new URL(getApiBaseUrl()).pathname.replace(/\/$/, "");
  if (url.pathname.replace(/\/$/, "") !== `${basePath}${expectedPath}`) throw new Error("API returned malformed pagination.");
  const raw = url.searchParams.get("page");
  if (!raw || !/^\d+$/.test(raw)) throw new Error("API returned malformed pagination.");
  const page = Number(raw);
  if (!Number.isSafeInteger(page) || page < 1) throw new Error("API returned malformed pagination.");
  return page;
}

export async function collectPages<T>(path: string, params: Record<string, string | number>, load: (page: number) => Promise<ApiPage<T>> = (page) => requestPage<T>(path, { ...params, page })) {
  const results: T[] = [];
  const visited = new Set<number>();
  let pageNumber = 1;
  while (true) {
    if (visited.has(pageNumber) || visited.size >= 1000) throw new Error("API returned malformed pagination.");
    visited.add(pageNumber);
    const page = await load(pageNumber);
    results.push(...page.results);
    if (!page.next) return results;
    pageNumber = nextPageNumber(page.next, path);
  }
}

export const getArtists = (search = "", page = 1, sort: ArtistSort = "wins") => requestPage<Artist>("/artists", { search: search.trim() || undefined, ordering: artistOrderings[sort], page });
export const getArtist = (id: number) => requestJson<Artist>(`/artists/${id}`);
export const getArtistSongs = (id: number, page = 1) => requestPage<Song>("/songs", { artist: id, ordering: "-total_wins,title", page });
export const getArtistWins = (id: number, page = 1) => requestPage<Win>("/wins", { artist: id, ordering: "-date", page });
export const getAllArtistSongs = (id: number) => collectPages<Song>("/songs", { artist: id, ordering: "-total_wins,title" });
export const getAllArtistWins = (id: number) => collectPages<Win>("/wins", { artist: id, ordering: "-date" });

async function safePage<T>(label: string, path: string, params?: Record<string, string | number>) {
  try { return { page: await requestPage<T>(path, params), error: undefined }; }
  catch (error) {
    return { page: { count: 0, next: null, previous: null, results: [] } as ApiPage<T>, error: `${label}: ${error instanceof Error ? error.message : "Could not load data."}` };
  }
}

export async function getHomeData(search = ""): Promise<HomeData> {
  const [artists, songs, wins, shows, artistResults] = await Promise.all([
    safePage<ArtistLeaderboardRow>("Artist leaderboard", "/leaderboards/artists", { limit: 5 }),
    safePage<SongLeaderboardRow>("Song leaderboard", "/leaderboards/songs", { limit: 5 }),
    safePage<Win>("Recent wins", "/wins", { page: 1 }),
    safePage<Show>("Music shows", "/shows"),
    search.trim() ? safePage<Artist>("Artist search", "/artists", { search: search.trim(), ordering: artistOrderings.wins, page: 1 }) : Promise.resolve({ page: { count: 0, next: null, previous: null, results: [] } as ApiPage<Artist>, error: undefined }),
  ]);
  return { artists: artists.page.results, songs: songs.page.results, wins: wins.page.results.slice(0, 8), shows: shows.page.results, artistResults: artistResults.page.results.slice(0, 8), artistResultCount: artistResults.page.count, errors: [artists.error, songs.error, wins.error, shows.error, artistResults.error].filter((error): error is string => Boolean(error)) };
}
