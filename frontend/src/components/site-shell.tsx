import Link from "next/link";
import { MobileNav } from "@/components/mobile-nav";

const links = [
  ["Home", "/"],
  ["Artists", "/#artists"],
  ["Songs", "/#songs"],
  ["Wins", "/#wins"],
  ["Shows", "/#shows"],
  ["About", "/#about"],
] as const;

export function SiteHeader() {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <Link href="/" className="group flex items-center gap-2" aria-label="KpopWins home">
          <span className="grid size-9 place-items-center border-2 border-foreground bg-brand-pink font-heading text-lg font-bold text-white shadow-[3px_3px_0_var(--foreground)] transition-transform group-hover:-translate-y-0.5">
            K
          </span>
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
  return (
    <footer id="about" className="mt-20 border-t border-border bg-card">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <p><span className="font-heading font-bold text-foreground">KpopWins</span> is a fan-made archive of Korean music-show wins.</p>
        <p className="text-xs">Not affiliated with artists, labels, or broadcasters.</p>
      </div>
    </footer>
  );
}
