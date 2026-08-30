import { ApiRequestError, parseApiPage, requestJson, serializeApiParams, type ApiParams, type ApiTransport, type CorrectionReport } from "@/lib/api-shared";

const browserApiBaseUrl = "/backend-api";

export function buildBrowserApiUrl(path: string, params: ApiParams = {}) {
  const query = serializeApiParams(params).toString();
  return `${browserApiBaseUrl}${path}${query ? `?${query}` : ""}`;
}

export async function browserRequestPage<T>(path: string, params?: ApiParams, signal?: AbortSignal) {
  return parseApiPage<T>(await requestJson<unknown>(buildBrowserApiUrl(path, params), signal));
}

export const browserTransport: ApiTransport = { requestPage: browserRequestPage };

export async function submitCorrection(report: CorrectionReport) {
  const response = await fetch(buildBrowserApiUrl("/corrections"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!response.ok) throw new ApiRequestError(response.status);
  return response.json() as Promise<{ detail: string }>;
}
