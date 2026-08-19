export type ApiPage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Artist = { id: number; name: string; total_wins?: number };
export type Song = { id: number; title: string; artist: Pick<Artist, "id" | "name">; total_wins?: number };
export type Show = { id: number; slug: string; name: string; active: boolean };
export type Win = { id: number; date: string; show: Show; song: Song };
export type ArtistLeaderboardRow = { rank: number; wins: number; artist: Pick<Artist, "id" | "name"> };
export type SongLeaderboardRow = { rank: number; wins: number; song: Song };

export type HomeData = {
  artists: ArtistLeaderboardRow[];
  songs: SongLeaderboardRow[];
  wins: Win[];
  shows: Show[];
  artistResults: Artist[];
  errors: string[];
};

const defaultBaseUrl = "http://127.0.0.1:8000/api/v1";

export function getApiBaseUrl() {
  return (
    process.env.DJANGO_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    defaultBaseUrl
  ).replace(/\/$/, "");
}

export function parseApiPage<T>(value: unknown): ApiPage<T> {
  if (!value || typeof value !== "object") throw new Error("API returned an invalid page.");
  const page = value as Record<string, unknown>;
  if (!Array.isArray(page.results) || typeof page.count !== "number") {
    throw new Error("API returned an invalid page.");
  }
  return {
    count: page.count,
    next: typeof page.next === "string" ? page.next : null,
    previous: typeof page.previous === "string" ? page.previous : null,
    results: page.results as T[],
  };
}

async function requestPage<T>(path: string, params?: Record<string, string | number>) {
  const search = params ? `?${new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))}` : "";
  const response = await fetch(`${getApiBaseUrl()}${path}${search}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`API request failed (${response.status}).`);
  return parseApiPage<T>(await response.json());
}

async function safePage<T>(label: string, path: string, params?: Record<string, string | number>) {
  try {
    return { page: await requestPage<T>(path, params), error: undefined };
  } catch (error) {
    return {
      page: { count: 0, next: null, previous: null, results: [] } as ApiPage<T>,
      error: `${label}: ${error instanceof Error ? error.message : "Could not load data."}`,
    };
  }
}

export async function getHomeData(search = ""): Promise<HomeData> {
  const [artists, songs, wins, shows, artistResults] = await Promise.all([
    safePage<ArtistLeaderboardRow>("Artist leaderboard", "/leaderboards/artists", { limit: 5 }),
    safePage<SongLeaderboardRow>("Song leaderboard", "/leaderboards/songs", { limit: 5 }),
    safePage<Win>("Recent wins", "/wins", { page: 1 }),
    safePage<Show>("Music shows", "/shows"),
    search.trim()
      ? safePage<Artist>("Artist search", "/artists", { search: search.trim(), page: 1 })
      : Promise.resolve({ page: { count: 0, next: null, previous: null, results: [] } as ApiPage<Artist>, error: undefined }),
  ]);
  return {
    artists: artists.page.results,
    songs: songs.page.results,
    wins: wins.page.results.slice(0, 8),
    shows: shows.page.results,
    artistResults: artistResults.page.results.slice(0, 8),
    errors: [artists.error, songs.error, wins.error, shows.error, artistResults.error].filter((error): error is string => Boolean(error)),
  };
}
