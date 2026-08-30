"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";
import { buildSearchUrl, normalizeSearchQuery } from "@/lib/search-params";

export function DebouncedArtistSearch({ id, query, className = "" }: { id: string; query: string; className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramsString = searchParams.toString();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef(query);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    valueRef.current = query;
    if (inputRef.current && inputRef.current.value !== query) inputRef.current.value = query;
  }, [query]);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const apply = useCallback((rawValue: string) => {
    if (timer.current) clearTimeout(timer.current);
    const nextQuery = normalizeSearchQuery(rawValue);
    const currentQuery = normalizeSearchQuery(new URLSearchParams(paramsString).get("search") ?? "");
    if (nextQuery === currentQuery) return;
    router.push(buildSearchUrl(pathname, paramsString, nextQuery), { scroll: false });
  }, [paramsString, pathname, router]);

  const schedule = useCallback((rawValue: string) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => apply(rawValue), 500);
  }, [apply]);

  return (
    <form onSubmit={(event) => { event.preventDefault(); apply(valueRef.current); }}>
      <label htmlFor={id} className="sr-only">Artist name or alias</label>
      <input
        id={id}
        ref={inputRef}
        defaultValue={query}
        onChange={(event) => {
          valueRef.current = event.target.value;
          schedule(event.target.value);
        }}
        placeholder="Artist name or alias"
        autoComplete="off"
        className={`min-h-12 w-full min-w-0 border-2 border-foreground bg-card px-4 text-base placeholder:text-muted-foreground ${className}`}
      />
    </form>
  );
}
