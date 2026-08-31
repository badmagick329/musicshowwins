import Link from "next/link";
import { Coffee } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { MobileNav } from "@/components/mobile-nav";
import { getSupportUrl } from "@/lib/support-url";

const links = [
  ["Home", "/"],
  ["Artists", "/artists"],
  ["Songs", "/songs"],
  ["Wins", "/wins"],
  ["Shows", "/shows"],
  ["About", "/about"],
] as const;

export function SiteHeader() {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <Link href="/" className="group flex items-center gap-2" aria-label="KpopWins home">
          <BrandMark className="size-9 transition-transform group-hover:-translate-y-0.5" />
          <span className="font-heading text-xl font-bold tracking-tight">KpopWins</span>
        </Link>
        <nav aria-label="Primary navigation" className="hidden items-center gap-1 md:flex">
          {links.map(([label, href]) => (
            <Link key={label} href={href} className="px-3 py-2 text-sm font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
              {label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/#search" className="hidden border border-foreground bg-highlight-yellow px-3 py-2 text-sm font-bold shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5 sm:inline-flex">
            Find an artist
          </Link>
          <MobileNav />
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const supportUrl = getSupportUrl();
  return (
    <footer id="about" className="mt-20 border-t border-border bg-card">
      <div className="mx-auto grid max-w-7xl gap-4 px-5 py-8 text-sm text-muted-foreground sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start lg:px-8">
        <div className="space-y-2">
          <p><span className="font-heading font-bold text-foreground">KpopWins</span> is a fan-made record of K-pop music show wins.</p>
          <p className="max-w-3xl text-xs leading-relaxed">Results come from <a href="https://en.wikipedia.org/" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-foreground">Wikipedia contributors</a> and are reviewed by KpopWins. Wikipedia content is available under <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-foreground">CC BY-SA 4.0</a>.</p>
        </div>
        {supportUrl && (
          <div className="flex flex-col items-start gap-4 sm:items-end">
            <a href={supportUrl} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-10 items-center gap-2 border border-foreground bg-highlight-yellow px-3 text-sm font-bold text-foreground shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5">
              <Coffee className="size-4" aria-hidden="true" />
              Buy me a coffee
            </a>
          </div>
        )}
      </div>
    </footer>
  );
}
