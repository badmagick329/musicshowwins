import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14">
      <div className="border-2 border-foreground bg-card p-6 sm:p-8">
        <h1 className="font-heading text-3xl font-bold">Page not found</h1>
        <p className="mt-2 text-muted-foreground">That page isn&apos;t in KpopWins.</p>
        <Link href="/" className="mt-5 inline-flex min-h-10 items-center border-2 border-foreground bg-highlight-yellow px-3 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">
          Return home
        </Link>
      </div>
    </main>
  );
}
