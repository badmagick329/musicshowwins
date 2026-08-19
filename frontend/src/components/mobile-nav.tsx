"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import Link from "next/link";

export const mobileNavLinks = [
  ["Home", "/"],
  ["Artists", "/#artists"],
  ["Songs", "/#songs"],
  ["Wins", "/#wins"],
  ["Shows", "/#shows"],
  ["About", "/#about"],
] as const;

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger className="inline-flex min-h-10 items-center gap-2 border border-foreground bg-card px-3 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5 md:hidden">
        <Menu className="size-4" aria-hidden="true" />
        <span>Menu</span>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-40 bg-section-ink/55 transition-opacity data-ending-style:opacity-0 data-starting-style:opacity-0" />
        <Dialog.Popup className="fixed inset-y-0 right-0 z-50 flex w-[min(22rem,calc(100vw-1rem))] flex-col border-l-2 border-foreground bg-card p-5 text-foreground shadow-[-8px_0_0_color-mix(in_srgb,var(--brand-pink)_22%,transparent)] transition-transform data-ending-style:translate-x-full data-starting-style:translate-x-full">
          <div className="flex items-center justify-between border-b-2 border-foreground pb-4">
            <Dialog.Title className="font-heading text-xl font-bold">Explore KpopWins</Dialog.Title>
            <Dialog.Close aria-label="Close menu" className="grid size-10 place-items-center border border-foreground bg-highlight-yellow transition-transform hover:-translate-y-0.5">
              <X className="size-5" aria-hidden="true" />
            </Dialog.Close>
          </div>
          <Dialog.Description className="mt-5 text-sm leading-relaxed text-muted-foreground">
            Jump to recent wins, leaderboards, and music shows.
          </Dialog.Description>
          <nav aria-label="Mobile navigation" className="mt-6 flex flex-col gap-2">
            {mobileNavLinks.map(([label, href]) => (
              <Link key={label} href={href} onClick={() => setOpen(false)} className="border-b border-border px-1 py-3 font-heading text-lg font-bold transition-colors hover:text-brand-pink">
                {label}
              </Link>
            ))}
          </nav>
          <div className="mt-auto border-t border-border pt-4 text-xs text-muted-foreground">
            Fan-made archive · 2014–today
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
