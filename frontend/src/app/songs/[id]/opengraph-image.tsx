import { notFound } from "next/navigation";
import { ApiRequestError, getSong } from "@/lib/api";
import { ogCard, ogImageSize } from "@/lib/og-card";
import { plural } from "@/lib/seo";

export const alt = "Song music show win summary on KpopWins";
export const size = ogImageSize;
export const contentType = "image/png";

export default async function SongOpenGraphImage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  try {
    const song = await getSong(Number(id));
    return ogCard({
      title: song.title,
      subtitle: `by ${song.artist.name}`,
      stats: `${song.total_wins} recorded ${plural(song.total_wins, "win")} · ${song.winning_shows} ${plural(song.winning_shows, "show")}`,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) notFound();
    throw error;
  }
}
