import { ImageResponse } from "next/og";

export const ogImageSize = { width: 1200, height: 630 };

// One card design for the site and every artist or song page, so shared links look like one
// brand. Long catalogue names shrink rather than wrap onto a third line.
export function ogCard({ title, subtitle, stats }: { title: string; subtitle: string; stats?: string }) {
  const titleSize = title.length > 40 ? 56 : title.length > 22 ? 68 : 84;
  return new ImageResponse(
    <div style={{ alignItems: "center", background: "#e9d8e8", color: "#241526", display: "flex", height: "100%", justifyContent: "center", padding: "72px", width: "100%" }}>
      <div style={{ background: "#ff3d81", border: "8px solid #241526", boxShadow: "18px 18px 0 #241526", display: "flex", flexDirection: "column", padding: "54px 64px", width: "100%" }}>
        {stats && <div style={{ color: "#241526", display: "flex", fontSize: 30, fontWeight: 800, marginBottom: 18 }}>KpopWins</div>}
        <div style={{ color: "white", display: "flex", fontSize: titleSize, fontWeight: 800, letterSpacing: "-2px", lineHeight: 1.05 }}>{title}</div>
        <div style={{ display: "flex", fontSize: 38, fontWeight: 700, marginTop: 20 }}>{subtitle}</div>
        {stats && <div style={{ background: "#241526", color: "white", display: "flex", fontSize: 32, fontWeight: 700, marginTop: 34, padding: "12px 22px", alignSelf: "flex-start" }}>{stats}</div>}
      </div>
    </div>,
    ogImageSize,
  );
}
