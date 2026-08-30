import type { Win } from "@/lib/api-shared";
import { EmptyState, WinRecord } from "@/components/data-display";

export function ArtistWinHistory({ wins }: { wins: Win[] }) {
  if (!wins.length) return <EmptyState message="No dated wins are recorded for this artist." />;
  return <div className="border border-border bg-card">{wins.map((win) => <WinRecord key={win.id} win={win} hideArtist />)}</div>;
}
