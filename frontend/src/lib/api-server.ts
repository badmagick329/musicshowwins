import "server-only";
import { artistOrderings, type ArtistSort } from "@/lib/artist-list";
import {
  buildApiUrl,
  parseApiPage,
  requestJson,
  type ApiPage,
  type ApiParams,
  type ApiTransport,
  type Artist,
  type ArtistLeaderboardRow,
  type HomeData,
  type Show,
  type Song,
  type SongLeaderboardRow,
  type Win,
} from "@/lib/api-shared";

const defaultBaseUrl = "http://127.0.0.1:8000/api/v1";

export function getServerApiBaseUrl() {
  return (process.env.DJANGO_API_BASE_URL ?? defaultBaseUrl).replace(/\/$/, "");
}

export function buildServerApiUrl(path: string, params: ApiParams = {}) {
  return buildApiUrl(getServerApiBaseUrl(), path, params);
}

export async function serverRequestPage<T>(path: string, params?: ApiParams, signal?: AbortSignal) {
  return parseApiPage<T>(await requestJson<unknown>(buildServerApiUrl(path, params), signal));
}

export const serverTransport: ApiTransport = { requestPage: serverRequestPage };

async function serverRequestJson<T>(path: string, signal?: AbortSignal) {
  return requestJson<T>(buildServerApiUrl(path), signal);
}

function nextPageNumber(next: string, expectedPath: string) {
  let url: URL;
  try { url = new URL(next, getServerApiBaseUrl()); } catch { throw new Error("API returned malformed pagination."); }
  const basePath = new URL(getServerApiBaseUrl()).pathname.replace(/\/$/, "");
  if (url.pathname.replace(/\/$/, "") !== `${basePath}${expectedPath}`) throw new Error("API returned malformed pagination.");
  const raw = url.searchParams.get("page");
  if (!raw || !/^\d+$/.test(raw)) throw new Error("API returned malformed pagination.");
  const page = Number(raw);
  if (!Number.isSafeInteger(page) || page < 1) throw new Error("API returned malformed pagination.");
  return page;
}

export async function collectPages<T>(path: string, params: Record<string, string | number>, load: (page: number) => Promise<ApiPage<T>> = (page) => serverRequestPage<T>(path, { ...params, page })) {
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

export const getArtists = (search = "", page = 1, sort: ArtistSort = "wins") => serverRequestPage<Artist>("/artists", { search: search.trim() || undefined, ordering: artistOrderings[sort], page });
export const getArtist = (id: number) => serverRequestJson<Artist>(`/artists/${id}`);
export const getSong = (id: number) => serverRequestJson<Song>(`/songs/${id}`);
export const getSongs = (search = "", page = 1, ordering = "-total_wins,title,artist__name") => serverRequestPage<Song>("/songs", { search: search.trim() || undefined, ordering, page });
export const getArtistSongs = (id: number, page = 1) => serverRequestPage<Song>("/songs", { artist: id, ordering: "-total_wins,title", page });
export const getArtistWins = (id: number, page = 1) => serverRequestPage<Win>("/wins", { artist: id, ordering: "-date", page });
export const getAllArtistSongs = (id: number) => collectPages<Song>("/songs", { artist: id, ordering: "-total_wins,title" });
export const getAllArtistWins = (id: number) => collectPages<Win>("/wins", { artist: id, ordering: "-date" });
export const getAllSongWins = (id: number) => collectPages<Win>("/wins", { song: id, ordering: "-date" });
export const getShows = () => serverRequestPage<Show>("/shows");

async function safePage<T>(label: string, path: string, params?: Record<string, string | number>) {
  try { return { page: await serverRequestPage<T>(path, params), error: undefined }; }
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
