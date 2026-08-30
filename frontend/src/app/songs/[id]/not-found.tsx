import Link from "next/link";

export default function SongNotFound() {
  return <main className="page-enter mx-auto max-w-7xl px-5 pb-8 pt-10 lg:px-8 lg:pt-14"><div className="border-2 border-foreground bg-card p-6 sm:p-8"><h1 className="font-heading text-3xl font-bold">Song not found</h1><p className="mt-2 text-muted-foreground">This song is not in the archive.</p><Link href="/songs" className="mt-5 inline-flex min-h-10 items-center border-2 border-foreground bg-highlight-yellow px-3 text-sm font-bold shadow-[2px_2px_0_var(--foreground)]">Browse songs</Link></div></main>;
}
