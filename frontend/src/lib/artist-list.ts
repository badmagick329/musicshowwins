export const artistSorts = ["wins", "name", "name-desc"] as const;
export type ArtistSort = (typeof artistSorts)[number];

export const artistSortLabels: Record<ArtistSort, string> = {
  wins: "Most wins",
  name: "Name A–Z",
  "name-desc": "Name Z–A",
};

export const artistOrderings: Record<ArtistSort, string> = {
  wins: "-total_wins,name",
  name: "name",
  "name-desc": "-name",
};

export function parseArtistSort(value: string | string[] | undefined): ArtistSort {
  return typeof value === "string" && artistSorts.includes(value as ArtistSort)
    ? (value as ArtistSort)
    : "wins";
}

export function artistsUrl({ search = "", sort = "wins", page = 1 }: { search?: string; sort?: ArtistSort; page?: number }) {
  const params = new URLSearchParams({ sort });
  if (search.trim()) params.set("search", search.trim());
  if (page > 1) params.set("page", String(page));
  return `/artists?${params}`;
}
