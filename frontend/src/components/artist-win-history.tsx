import type { Win } from "@/lib/api-shared";
import { EmptyState, WinRecord } from "@/components/data-display";

export function ArtistWinHistory({ wins, emptyMessage = "No dated wins are recorded for this artist." }: { wins: Win[]; emptyMessage?: string }) {
  if (!wins.length) return <EmptyState message={emptyMessage} />;
  return <div className="border border-border bg-card">{wins.map((win) => <WinRecord key={win.id} win={win} hideArtist />)}</div>;
}
