"use client";

import { useCallback, useEffect, useRef } from "react";

export function usePaginationScroll(page: number, isPageReady: boolean, targetId: string) {
  const pendingPage = useRef<number | null>(null);

  useEffect(() => {
    if (!isPageReady || pendingPage.current !== page) return;
    pendingPage.current = null;
    document.getElementById(targetId)?.scrollIntoView({ block: "start" });
  }, [isPageReady, page, targetId]);

  const requestPaginationScroll = useCallback((nextPage: number) => {
    pendingPage.current = nextPage;
  }, []);

  const cancelPaginationScroll = useCallback(() => {
    pendingPage.current = null;
  }, []);

  return { requestPaginationScroll, cancelPaginationScroll };
}
