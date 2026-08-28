export function normalizeSearchQuery(value: string) {
  return value.trim();
}

export function buildSearchUrl(pathname: string, currentParams: string, value: string) {
  const params = new URLSearchParams(currentParams);
  const query = normalizeSearchQuery(value);
  if (query) params.set("search", query);
  else params.delete("search");
  params.delete("page");
  const search = params.toString();
  return search ? `${pathname}?${search}` : pathname;
}
