import Link from "next/link";

export default function ArtistNotFound() {
  return <main className="mx-auto max-w-7xl px-5 py-10 lg:px-8"><div className="border-2 border-foreground bg-card p-8"><h1 className="font-heading text-3xl font-bold">Artist not found</h1><p className="mt-2 text-muted-foreground">That artist isn&apos;t in KpopWins.</p><Link href="/artists" className="mt-5 inline-flex border-2 border-foreground bg-highlight-yellow px-4 py-2 font-bold">View all artists</Link></div></main>;
}
