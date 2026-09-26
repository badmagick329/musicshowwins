import type { Artist } from "@/lib/api-shared";

export const artistPath = (artist: Pick<Artist, "slug">) => `/artists/${artist.slug}`;
