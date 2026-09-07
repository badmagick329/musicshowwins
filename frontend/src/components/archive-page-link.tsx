"use client";

import type { ReactNode } from "react";

// Keep pagination discoverable without giving up in-place archive navigation.
export function ArchivePageLink({ href, onNavigate, children }: { href: string; onNavigate: () => void; children: ReactNode }) {
  return <a href={href} onClick={(event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onNavigate();
  }} className="inline-flex min-h-11 items-center border-2 border-foreground bg-card px-4 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">{children}</a>;
}
