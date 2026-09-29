import type { Artist, Song, Win } from "@/lib/api-shared";
import { artistPath } from "@/lib/paths";
import { siteUrl } from "@/lib/seo";

// Stable @ids let search engines join an artist's page, its songs' pages and each song's
// byArtist reference into one entity graph. schema.org's MusicGroup explicitly covers solo
// musicians, and the catalogue does not distinguish groups from soloists.
const artistId = (artist: Pick<Artist, "slug">) => `${siteUrl}${artistPath(artist)}#artist`;
const songId = (song: Pick<Song, "id">) => `${siteUrl}/songs/${song.id}#song`;

export function artistJsonLd(artist: Artist, wins: Win[], description: string) {
  const songs = new Map<number, { song: Win["song"]; wins: number }>();
  for (const win of wins) {
    const entry = songs.get(win.song.id);
    if (entry) entry.wins += 1;
    else songs.set(win.song.id, { song: win.song, wins: 1 });
  }
  const tracks = [...songs.values()].sort((a, b) => b.wins - a.wins || a.song.title.localeCompare(b.song.title));
  return {
    "@context": "https://schema.org",
    "@type": "MusicGroup",
    "@id": artistId(artist),
    name: artist.name,
    description,
    mainEntityOfPage: `${siteUrl}${artistPath(artist)}`,
    track: tracks.map(({ song }) => ({ "@type": "MusicRecording", "@id": songId(song), name: song.title, url: `${siteUrl}/songs/${song.id}` })),
  };
}

export function songJsonLd(song: Song, description: string) {
  return {
    "@context": "https://schema.org",
    "@type": "MusicRecording",
    "@id": songId(song),
    name: song.title,
    description,
    mainEntityOfPage: `${siteUrl}/songs/${song.id}`,
    byArtist: { "@type": "MusicGroup", "@id": artistId(song.artist), name: song.artist.name, url: `${siteUrl}${artistPath(song.artist)}` },
  };
}
