"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { buildSearchUrl, normalizeSearchQuery } from "@/lib/search-params";

export function DebouncedArtistSearch({ id, query, className = "" }: { id: string; query: string; className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramsString = searchParams.toString();
  const [value, setValue] = useState(query);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const apply = useCallback((rawValue: string) => {
    if (timer.current) clearTimeout(timer.current);
    const nextQuery = normalizeSearchQuery(rawValue);
    const currentQuery = normalizeSearchQuery(new URLSearchParams(paramsString).get("search") ?? "");
    if (nextQuery === currentQuery) return;
    router.push(buildSearchUrl(pathname, paramsString, nextQuery), { scroll: false });
  }, [paramsString, pathname, router]);

  useEffect(() => {
    timer.current = setTimeout(() => apply(value), 500);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [apply, value]);

  return (
    <form onSubmit={(event) => { event.preventDefault(); apply(value); }}>
      <label htmlFor={id} className="sr-only">Artist name or alias</label>
      <input
        id={id}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Artist name or alias"
        autoComplete="off"
        className={`min-h-12 w-full min-w-0 border-2 border-foreground bg-card px-4 text-base placeholder:text-muted-foreground ${className}`}
      />
    </form>
  );
}
