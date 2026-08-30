import { parseApiPage, requestJson, serializeApiParams, type ApiParams, type ApiTransport } from "@/lib/api-shared";

const browserApiBaseUrl = "/backend-api";

export function buildBrowserApiUrl(path: string, params: ApiParams = {}) {
  const query = serializeApiParams(params).toString();
  return `${browserApiBaseUrl}${path}${query ? `?${query}` : ""}`;
}

export async function browserRequestPage<T>(path: string, params?: ApiParams, signal?: AbortSignal) {
  return parseApiPage<T>(await requestJson<unknown>(buildBrowserApiUrl(path, params), signal));
}

export const browserTransport: ApiTransport = { requestPage: browserRequestPage };
