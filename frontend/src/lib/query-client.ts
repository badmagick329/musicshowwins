import { ApiRequestError } from "@/lib/api-shared";
import { QueryClient } from "@tanstack/react-query";

export const archiveStaleTime = 60_000;

export function retryArchiveRequest(failureCount: number, error: unknown) {
  if (error instanceof ApiRequestError) return error.status >= 500 && failureCount < 2;
  return failureCount < 2;
}

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: archiveStaleTime,
        retry: retryArchiveRequest,
        refetchInterval: false,
        refetchOnWindowFocus: false,
      },
    },
  });
}
