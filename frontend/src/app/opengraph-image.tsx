import { ogCard, ogImageSize } from "@/lib/og-card";

export const alt = "KpopWins, K-pop music show wins and artist rankings";
export const size = ogImageSize;
export const contentType = "image/png";

export default function OpenGraphImage() {
  return ogCard({ title: "KpopWins", subtitle: "K-pop music show wins & artist rankings" });
}
