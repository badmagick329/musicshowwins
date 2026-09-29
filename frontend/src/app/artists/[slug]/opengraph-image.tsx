import { notFound } from "next/navigation";
import { ApiRequestError, getArtist } from "@/lib/api";
import { ogCard, ogImageSize } from "@/lib/og-card";
import { plural } from "@/lib/seo";

export const alt = "Artist music show win summary on KpopWins";
export const size = ogImageSize;
export const contentType = "image/png";

export default async function ArtistOpenGraphImage({ params }: { params: Promise<{ slug: string }> }) {
  try {
    const artist = await getArtist((await params).slug);
    return ogCard({
      title: artist.name,
      subtitle: "K-pop music show wins",
      stats: `${artist.total_wins} recorded ${plural(artist.total_wins, "win")} · ${artist.winning_songs} winning ${plural(artist.winning_songs, "song")}`,
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) notFound();
    throw error;
  }
}
