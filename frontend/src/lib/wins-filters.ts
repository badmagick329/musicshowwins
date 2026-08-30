import { parsePositivePage } from "@/lib/api-shared";

export const archiveStartYear = 2014;
export const winsOrderings = ["-date", "date"] as const;
export type WinsOrdering = (typeof winsOrderings)[number];
export type WinsFilters = {
  search: string;
  show: string;
  year?: number;
  dateFrom: string;
  dateTo: string;
  ordering: WinsOrdering;
  page: number;
};
export type WinsSearchParams = Record<string, string | string[] | undefined>;

export function currentArchiveYear(now = new Date()) {
  return now.getFullYear();
}

export function defaultWinsFilters(): WinsFilters {
  return { search: "", show: "", year: undefined, dateFrom: "", dateTo: "", ordering: "-date", page: 1 };
}

function single(value: string | string[] | undefined) {
  return typeof value === "string" ? value : undefined;
}

function validDate(value: string | undefined) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? "" : value;
}

export function normalizeWinsFilters(filters: Partial<WinsFilters>, now = new Date()): WinsFilters {
  const defaults = defaultWinsFilters();
  const year = typeof filters.year === "number" && Number.isInteger(filters.year) && filters.year >= archiveStartYear && filters.year <= currentArchiveYear(now) ? filters.year : undefined;
  return {
    search: typeof filters.search === "string" ? filters.search.trim() : defaults.search,
    show: typeof filters.show === "string" ? filters.show.trim() : defaults.show,
    year,
    dateFrom: validDate(filters.dateFrom),
    dateTo: validDate(filters.dateTo),
    ordering: filters.ordering === "date" || filters.ordering === "-date" ? filters.ordering : defaults.ordering,
    page: typeof filters.page === "number" && Number.isSafeInteger(filters.page) && filters.page > 0 ? filters.page : defaults.page,
  };
}

export function parseWinsFilters(params: WinsSearchParams, now = new Date()) {
  const rawYear = single(params.year);
  return normalizeWinsFilters({
    search: single(params.search),
    show: single(params.show),
    year: rawYear && /^\d{4}$/.test(rawYear) ? Number(rawYear) : undefined,
    dateFrom: single(params.date_from),
    dateTo: single(params.date_to),
    ordering: single(params.ordering) as WinsOrdering | undefined,
    page: parsePositivePage(params.page),
  }, now);
}

export function winsDateRangeError(filters: WinsFilters) {
  return filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo
    ? "Start date must be on or before end date."
    : null;
}

export function winsApiParams(filters: WinsFilters) {
  return {
    search: filters.search || undefined,
    show: filters.show || undefined,
    year: filters.year,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
    ordering: filters.ordering,
    page: filters.page,
  };
}

export function serializeWinsFilters(filters: WinsFilters) {
  const normalized = normalizeWinsFilters(filters);
  const params = new URLSearchParams();
  if (normalized.search) params.set("search", normalized.search);
  if (normalized.show) params.set("show", normalized.show);
  if (normalized.year) params.set("year", String(normalized.year));
  if (normalized.dateFrom) params.set("date_from", normalized.dateFrom);
  if (normalized.dateTo) params.set("date_to", normalized.dateTo);
  if (normalized.ordering !== "-date") params.set("ordering", normalized.ordering);
  if (normalized.page > 1) params.set("page", String(normalized.page));
  return params;
}

export function winsUrl(filters: WinsFilters) {
  const search = serializeWinsFilters(filters).toString();
  return search ? `/wins?${search}` : "/wins";
}

export function updateWinsFilters(filters: WinsFilters, update: Partial<WinsFilters>) {
  const current = normalizeWinsFilters(filters);
  const candidate = normalizeWinsFilters({ ...current, ...update, page: update.page ?? current.page });
  const responseChangingKeys: (keyof WinsFilters)[] = ["search", "show", "year", "dateFrom", "dateTo", "ordering"];
  const resetPage = responseChangingKeys.some((key) => candidate[key] !== current[key]);
  return { ...candidate, page: resetPage ? 1 : candidate.page };
}

export function hasActiveWinsFilters(filters: WinsFilters) {
  const defaults = defaultWinsFilters();
  return filters.search !== defaults.search || filters.show !== defaults.show || filters.year !== defaults.year || filters.dateFrom !== defaults.dateFrom || filters.dateTo !== defaults.dateTo || filters.ordering !== defaults.ordering;
}

export function archiveYears(now = new Date()) {
  return Array.from({ length: currentArchiveYear(now) - archiveStartYear + 1 }, (_, index) => currentArchiveYear(now) - index);
}
