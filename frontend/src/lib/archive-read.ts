import "server-only";
import { AsyncLocalStorage } from "node:async_hooks";
import { unstable_cache } from "next/cache";
import { ApiRequestError } from "@/lib/api-shared";

export const publicArchiveCacheTag = "public-archive";
export const publicArchiveRevalidateSeconds = 86_400;
const warming = new AsyncLocalStorage<boolean>();

export function internalRequestHeaders() {
  const headers: Record<string, string> = { "X-Forwarded-Proto": "https" };
  const secret = process.env.INTERNAL_API_SECRET;
  if (secret) headers["X-KpopWins-Internal-Key"] = secret;
  return headers;
}

export class ArchiveRequestError extends ApiRequestError {
  constructor(status: number, public retryAfter: string | null) { super(status); }
}

// Only the authenticated warmer enters this context. The URL is intentionally
// the sole cache argument: warm and public reads return identical catalogue data.
// No visitor headers or cancellation signals may alter this shared cache key.
async function loadArchive(url: string) {
  const headers = internalRequestHeaders();
  if (!warming.getStore()) headers["X-KpopWins-Public-Read"] = "1";
  return fetchArchive(url, headers);
}

async function fetchArchive(url: string, headers: Record<string, string>, signal?: AbortSignal) {
  const response = await fetch(url, { headers, signal, cache: "no-store", redirect: "manual" });
  if (!response.ok) throw new ArchiveRequestError(response.status, response.headers.get("retry-after"));
  return { data: await response.json() as unknown, status: response.status, contentType: response.headers.get("content-type") };
}

// Next includes Function#toString in its cache key. Compiled route and SSR
// bundles rename loader identifiers differently; a bound callback has the same
// native source in each bundle. Bump this explicit version whenever cache
// semantics change, since loader source changes no longer invalidate old data.
const cachedRead = unstable_cache(loadArchive.bind(null), ["archive-json-v2"], {
  revalidate: publicArchiveRevalidateSeconds, tags: [publicArchiveCacheTag],
});

export async function readArchive(url: string, signal?: AbortSignal) {
  // Aborting one render must not cancel a fill used by other visitors.
  signal?.throwIfAborted();
  const response = await cachedRead(canonicalArchiveUrl(url));
  signal?.throwIfAborted();
  return response;
}

export async function readPublicArchiveUncached(url: string, signal?: AbortSignal) {
  // Next Proxy has a separate runtime without the app's persistent data cache.
  // Always charge its redirect lookup to the public budget, even in warm context.
  const headers = { ...internalRequestHeaders(), "X-KpopWins-Public-Read": "1" };
  return fetchArchive(canonicalArchiveUrl(url), headers, signal);
}

export function warmArchive<T>(load: () => Promise<T>) {
  return warming.run(true, load);
}

const filterKeys = ["search", "artist", "song", "show", "year", "date_from", "date_to", "ordering", "page"];
const allowedKeys: Record<string, string[]> = {
  artists: filterKeys,
  songs: filterKeys,
  wins: filterKeys,
  shows: ["search", "ordering", "page"],
  episodes: ["date_from", "date_to", "page"],
  "leaderboards/artists": ["limit", "show", "year", "date_from", "date_to", "page"],
  "leaderboards/songs": ["limit", "show", "year", "date_from", "date_to", "page"],
  sitemap: [],
};
const orderingFields: Record<string, Set<string>> = {
  artists: new Set(["name", "id", "total_wins"]),
  songs: new Set(["title", "id", "total_wins", "artist__name"]),
  wins: new Set(["date", "id", "show__name", "song__title", "song__artist__name"]),
  shows: new Set(["name", "slug", "id"]),
};

export function canonicalArchiveUrl(value: string) {
  const url = new URL(value);
  const match = url.pathname.match(/\/api\/v1\/(.+?)\/?$/);
  const path = match?.[1];
  if (!path) throw new ApiRequestError(404);
  const detail = path.match(/^(artists|songs)\/([^/]+)$/);
  if (detail) {
    const key = detail[2];
    if (detail[1] === "songs" || /^\d+$/.test(key)) {
      const id = Number(key);
      if (!/^\d+$/.test(key) || !Number.isSafeInteger(id) || id < 1 || id > 2_147_483_647) throw new ApiRequestError(404);
      url.pathname = url.pathname.replace(/[^/]+\/?$/, String(id));
    } else if (!/^[a-z0-9_-]{1,200}$/.test(key)) throw new ApiRequestError(404);
    url.search = "";
    return url.toString();
  }
  if (!Object.hasOwn(allowedKeys, path)) throw new ApiRequestError(404);
  const keys = allowedKeys[path];
  const params = new URLSearchParams();
  for (const key of keys) {
    const raw = url.searchParams.get(key)?.trim();
    if (!raw) continue;
    let normalized = raw;
    if (["page", "limit", "year"].includes(key)) {
      const number = Number(raw);
      if (!/^\d+$/.test(raw) || !Number.isSafeInteger(number) || number < 1 || number > (key === "limit" ? 1000 : key === "year" ? 9999 : 1_000_000)) throw new ApiRequestError(400);
      normalized = String(number);
    } else if (key === "date_from" || key === "date_to") {
      const date = new Date(`${raw}T00:00:00Z`);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(raw) || Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== raw) throw new ApiRequestError(400);
    } else if (key === "ordering") {
      const parts = raw.split(",").map((part) => part.trim());
      if (parts.length > orderingFields[path].size || parts.some((part) => !orderingFields[path].has(part.replace(/^-/, ""))) || new Set(parts.map((part) => part.replace(/^-/, ""))).size !== parts.length) throw new ApiRequestError(400);
      normalized = parts.join(",");
    } else if (raw.length > 200) throw new ApiRequestError(400);
    params.set(key, normalized);
  }
  url.pathname = url.pathname.replace(/\/$/, "");
  url.search = params.toString();
  return url.toString();
}
