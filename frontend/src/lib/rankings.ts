import { archiveStartYear } from "@/lib/wins-filters";
import { parsePositivePage, type ApiParams } from "@/lib/api-shared";

export type RankingKind = "songs" | "artists";
export type RankingPeriod = "year" | "all-time" | "custom";
export type RankingSelection = {
  kind: RankingKind;
  period: RankingPeriod;
  year: number;
  dateFrom: string;
  dateTo: string;
  page: number;
  error: string | null;
};
export type RankingSearchParams = Record<string, string | string[] | undefined>;

export function archiveToday(now = new Date()) {
  return now.toISOString().slice(0, 10);
}

function single(value: string | string[] | undefined) {
  return typeof value === "string" ? value : undefined;
}

function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function parseRankingSelection(params: RankingSearchParams, today = archiveToday()): RankingSelection {
  const currentYear = Number(today.slice(0, 4));
  const rawKind = single(params.kind);
  const rawPeriod = single(params.period);
  const rawYear = single(params.year);
  const kind = rawKind === "artists" ? "artists" : "songs";
  const period = rawPeriod === "all-time" || rawPeriod === "custom" ? rawPeriod : "year";
  const year = rawYear && /^\d{4}$/.test(rawYear) ? Number(rawYear) : currentYear;
  const dateFrom = single(params.date_from) ?? "";
  const dateTo = single(params.date_to) ?? "";
  let error: string | null = null;
  if (rawKind && rawKind !== "songs" && rawKind !== "artists") error = "Choose Songs or Artists.";
  else if (rawPeriod && rawPeriod !== "all-time" && rawPeriod !== "custom" && rawPeriod !== "year") error = "Choose a valid period.";
  else if (period === "year" && (year < archiveStartYear || year > currentYear || (rawYear && !/^\d{4}$/.test(rawYear)))) error = "Choose an archive year.";
  else if (period !== "year" && rawYear) error = "Choose a year or another period, not both.";
  else if (period === "custom" && (!validDate(dateFrom) || !validDate(dateTo))) error = "Enter valid start and end dates.";
  else if (period === "custom" && dateFrom > dateTo) error = "Start date must be on or before end date.";
  else if (period !== "custom" && (dateFrom || dateTo)) error = "Choose a date range or another period, not both.";
  return { kind, period, year, dateFrom, dateTo, page: parsePositivePage(params.page), error };
}

export function rankingApiParams(selection: RankingSelection, today = archiveToday()): ApiParams {
  if (selection.period === "all-time") return { page: selection.page };
  if (selection.period === "custom") return { date_from: selection.dateFrom, date_to: selection.dateTo, page: selection.page };
  return {
    date_from: `${selection.year}-01-01`,
    date_to: selection.year === Number(today.slice(0, 4)) ? today : `${selection.year}-12-31`,
    page: selection.page,
  };
}

export function rankingUrl(selection: RankingSelection, today = archiveToday()) {
  const params = new URLSearchParams();
  if (selection.kind === "artists") params.set("kind", "artists");
  if (selection.period === "all-time") params.set("period", "all-time");
  else if (selection.period === "custom") {
    params.set("period", "custom");
    params.set("date_from", selection.dateFrom);
    params.set("date_to", selection.dateTo);
  } else if (selection.year !== Number(today.slice(0, 4))) params.set("year", String(selection.year));
  if (selection.page > 1) params.set("page", String(selection.page));
  const query = params.toString();
  return `/rankings${query ? `?${query}` : ""}`;
}

export function rankingHeading(selection: RankingSelection) {
  const subject = selection.kind === "songs" ? "songs" : "artists";
  if (selection.period === "all-time") return `Top ${subject} of all time`;
  if (selection.period === "custom") return `Top ${subject} from ${selection.dateFrom} to ${selection.dateTo}`;
  return `Top ${subject} of ${selection.year}`;
}

export function rankingWinsUrl(selection: RankingSelection, id: number, today = archiveToday()) {
  const params = new URLSearchParams();
  params.set(selection.kind === "songs" ? "song" : "artist", String(id));
  const period = rankingApiParams(selection, today);
  if (period.date_from) params.set("date_from", String(period.date_from));
  if (period.date_to) params.set("date_to", String(period.date_to));
  return `/wins?${params.toString()}#wins-results-title`;
}
