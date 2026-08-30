import { defaultWinsFilters, parseWinsFilters, updateWinsFilters, winsUrl, type WinsFilters } from "@/lib/wins-filters";

export type HistoryMode = "push" | "replace";

export function winsFiltersFromSearchParams(searchParams: URLSearchParams) {
  const params: Record<string, string> = {};
  searchParams.forEach((value, key) => { params[key] = value; });
  return parseWinsFilters(params);
}

export function nextWinsNavigation(current: WinsFilters, update: Partial<WinsFilters>, mode: HistoryMode = "push") {
  const filters = updateWinsFilters(current, update);
  const url = winsUrl(filters);
  return url === winsUrl(current) ? null : { filters, url, mode };
}

export function clearWinsNavigation(current: WinsFilters) {
  return nextWinsNavigation(current, defaultWinsFilters());
}

export function writeWinsHistory(current: WinsFilters, update: Partial<WinsFilters>, mode: HistoryMode = "push") {
  const navigation = nextWinsNavigation(current, update, mode);
  if (!navigation) return false;
  window.history[`${navigation.mode}State`](null, "", navigation.url);
  return true;
}
